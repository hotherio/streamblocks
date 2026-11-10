"""What a syntax needs to know about a block to write its grammar rule."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum, auto
from typing import TYPE_CHECKING, Any, Protocol, cast

from hother.streamblocks.core.models import extract_block_types
from hother.streamblocks.grammar.nodes import zero_or_more

if TYPE_CHECKING:
    from hother.streamblocks.core.models import Block
    from hother.streamblocks.core.types import BaseContent
    from hother.streamblocks.grammar.nodes import Node

_ID_FIELD = "id"
_BLOCK_TYPE_FIELD = "block_type"
_NULL_TYPE = "null"


class GrammarError(ValueError):
    """A grammar cannot be built for this registry."""


class LineFactory(Protocol):
    """Builds a content line that avoids the syntax's own markers plus extra prefixes."""

    def __call__(self, *prefixes: str, non_blank: bool = False) -> Node:
        """Return a full line that starts with none of the syntax markers nor ``prefixes``."""
        ...


class FieldKind(StrEnum):
    """How a metadata value is constrained."""

    STRING = auto()
    INTEGER = auto()
    NUMBER = auto()
    BOOLEAN = auto()
    ENUM = auto()
    ANY = auto()


_KINDS_BY_JSON_TYPE = {
    "string": FieldKind.STRING,
    "integer": FieldKind.INTEGER,
    "number": FieldKind.NUMBER,
    "boolean": FieldKind.BOOLEAN,
}


@dataclass(frozen=True, slots=True)
class MetadataField:
    """One metadata field of a block, as far as the grammar is concerned.

    Attributes:
        name: Field name
        kind: Value constraint
        required: The field must be present
        choices: Allowed values when ``kind`` is :attr:`FieldKind.ENUM`
        non_empty: A string value must have at least one character
    """

    name: str
    kind: FieldKind
    required: bool
    choices: tuple[str, ...] = ()
    non_empty: bool = False


@dataclass(frozen=True, slots=True)
class BlockSpec:
    """A registered block type, its metadata fields (``id`` and ``block_type`` excluded) and its content class."""

    block_type: str
    fields: tuple[MetadataField, ...]
    content_class: type[BaseContent]

    def content(self, line: LineFactory) -> Node:
        """The content section: the content class's own grammar, or any lines accepted by ``line``."""
        custom = self.content_class.grammar(line)
        return custom if custom is not None else zero_or_more(line())


@dataclass(slots=True)
class SyntaxGrammar:
    """The grammar rules a syntax contributes.

    Attributes:
        text_line: A line of free text that cannot be mistaken for a block opening
        blocks: One node per block type, matching a whole block including its final line break
        shared: Named helper rules that the nodes above refer to with ``Ref``
    """

    text_line: Node
    blocks: dict[str, Node]
    shared: dict[str, Node] = field(default_factory=dict[str, "Node"])


def block_spec(block_type: str, block_class: type[Block[Any, Any]]) -> BlockSpec:
    """Describe ``block_class``'s metadata fields from its JSON schema."""
    metadata_class, content_class = extract_block_types(block_class)
    schema = metadata_class.model_json_schema()
    required = set(cast("list[str]", schema.get("required", [])))
    properties = cast("dict[str, dict[str, Any]]", schema.get("properties", {}))
    fields = tuple(
        _metadata_field(name, definition, required=name in required)
        for name, definition in properties.items()
        if name not in {_ID_FIELD, _BLOCK_TYPE_FIELD}
    )
    return BlockSpec(block_type=block_type, fields=fields, content_class=content_class)


def _metadata_field(name: str, definition: dict[str, Any], *, required: bool) -> MetadataField:
    """Map one JSON-schema property to a field description."""
    variants = cast("list[dict[str, Any]]", definition.get("anyOf", [definition]))
    concrete = [variant for variant in variants if variant.get("type") != _NULL_TYPE]
    if len(concrete) != 1:
        return MetadataField(name=name, kind=FieldKind.ANY, required=required)

    (variant,) = concrete
    choices = cast("list[Any]", variant.get("enum", [variant["const"]] if "const" in variant else []))
    if choices:
        return MetadataField(name=name, kind=FieldKind.ENUM, required=required, choices=tuple(map(str, choices)))

    kind = _KINDS_BY_JSON_TYPE.get(str(variant.get("type")), FieldKind.ANY)
    non_empty = kind is FieldKind.STRING and int(variant.get("minLength", 0)) > 0
    return MetadataField(name=name, kind=kind, required=required, non_empty=non_empty)
