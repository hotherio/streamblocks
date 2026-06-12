"""Build LLM prompt context and text from block classes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from hother.streamblocks.core.models import extract_block_types
from hother.streamblocks.prompts.inspector import inspect_content_format, parse_block_docstring
from hother.streamblocks.prompts.manager import TemplateManager

if TYPE_CHECKING:
    from hother.streamblocks.core.models import Block
    from hother.streamblocks.core.types import BaseContent, BaseMetadata
    from hother.streamblocks.syntaxes.base import BaseSyntax

_METADATA_FIELD = "metadata"
_CONTENT_FIELD = "content"
# Fields excluded from generated schemas because they are auto-populated.
_ALWAYS_EXCLUDED: dict[str, set[str]] = {
    _METADATA_FIELD: {"id", "block_type"},
    _CONTENT_FIELD: {"raw_content"},
}


def generate_block_prompt(
    block_class: type[Block[Any, Any]],
    syntax: BaseSyntax,
    *,
    include_examples: bool = True,
    template_version: str = "default",
    description: str = "",
) -> str:
    """Generate an instruction prompt for a single block type.

    Args:
        block_class: The block class to document.
        syntax: Syntax used to describe the format and serialize examples.
        include_examples: Whether to render examples from ``get_examples()``.
        template_version: Template version for A/B testing.
        description: Optional description overriding the block docstring.

    Returns:
        The rendered prompt for this block type.
    """
    context: dict[str, Any] = {
        "syntax_name": type(syntax).__name__,
        "syntax_format": syntax.describe_format(),
        "block": build_block_context(
            block_class,
            syntax,
            include_examples=include_examples,
            description=description,
        ),
    }
    return TemplateManager().render(context, template_version, mode="single")


def build_block_context(
    block_class: type[Block[Any, Any]],
    syntax: BaseSyntax,
    *,
    include_examples: bool = True,
    description: str = "",
) -> dict[str, Any]:
    """Build the template context describing a single block type."""
    metadata_class, content_class = extract_block_types(block_class)
    block_description, block_usage = parse_block_docstring(block_class)

    examples = [syntax.serialize_block(example) for example in block_class.get_examples()] if include_examples else []

    return {
        "name": infer_block_type_name(block_class),
        "description": description or block_description,
        "usage": block_usage,
        "content_format": inspect_content_format(content_class),
        "metadata_schema": extract_schema(metadata_class, _METADATA_FIELD),
        "content_schema": extract_schema(content_class, _CONTENT_FIELD),
        "examples": examples,
    }


def infer_block_type_name(block_class: type[Block[Any, Any]]) -> str:
    """Infer the block type name from its metadata, falling back to snake_case."""
    metadata_class, _ = extract_block_types(block_class)
    declared = _declared_block_type(metadata_class)
    return declared if declared is not None else _to_snake_case(block_class.__name__)


def _declared_block_type(metadata_class: type[BaseMetadata]) -> str | None:
    """Read the declared default of the metadata ``block_type`` field."""
    field = metadata_class.model_fields.get("block_type")
    default = getattr(field, "default", None)
    return default if isinstance(default, str) and default else None


def _to_snake_case(name: str) -> str:
    """Convert a CamelCase class name to snake_case."""
    chars: list[str] = []
    for index, char in enumerate(name):
        if char.isupper() and index > 0:
            chars.append("_")
        chars.append(char.lower())
    return "".join(chars)


def extract_schema(
    model_class: type[BaseMetadata | BaseContent],
    field_type: str,
    *,
    exclude_fields: set[str] | None = None,
) -> dict[str, Any]:
    """Extract a filtered JSON schema for a metadata or content model."""
    return filter_schema_fields(model_class.model_json_schema(), field_type, exclude_fields=exclude_fields)


def filter_schema_fields(
    schema: dict[str, Any],
    field_type: str,
    *,
    exclude_fields: set[str] | None = None,
) -> dict[str, Any]:
    """Remove auto-populated and caller-excluded fields from a JSON schema."""
    excluded = set(_ALWAYS_EXCLUDED.get(field_type, set()))
    if exclude_fields:
        excluded |= exclude_fields

    if "properties" not in schema:
        return schema

    filtered = dict(schema)
    filtered["properties"] = {key: value for key, value in schema["properties"].items() if key not in excluded}
    if "required" in filtered:
        filtered["required"] = [name for name in filtered["required"] if name not in excluded]
    return filtered
