"""Grammar nodes for metadata values, shared by the built-in syntaxes."""

from __future__ import annotations

from hother.streamblocks.grammar.nodes import (
    LINE_CHAR,
    CharSet,
    Node,
    choice,
    one_or_more,
    optional,
    seq,
    zero_or_more,
)
from hother.streamblocks.grammar.spec import FieldKind, MetadataField

IDENTIFIER_RULE = "identifier"
IDENTIFIER = one_or_more(CharSet(chars="_-", ranges=(("A", "Z"), ("a", "z"), ("0", "9"))))
"""A block identifier: letters, digits, underscores and dashes."""

WORD_RULE = "word"
WORD = one_or_more(CharSet(chars="_", ranges=(("A", "Z"), ("a", "z"), ("0", "9"))))
"""Letters, digits and underscores (what ``\\w+`` matches in ASCII)."""

_DIGIT = CharSet(ranges=(("0", "9"),))
_INTEGER = seq(optional(seq("-")), one_or_more(_DIGIT))
_NUMBER = seq(_INTEGER, optional(seq(".", one_or_more(_DIGIT))))
_BOOLEAN = choice("true", "false")


def scalar(metadata_field: MetadataField, *, string: Node, fallback: Node | None = None) -> Node:
    """The node for a field's value.

    Args:
        metadata_field: Field to render
        string: Node for a free string value, which depends on the syntax's quoting
        fallback: Node for values the grammar cannot type (defaults to any non-empty line text)
    """
    match metadata_field.kind:
        case FieldKind.ENUM:
            return choice(*metadata_field.choices)
        case FieldKind.INTEGER:
            return _INTEGER
        case FieldKind.NUMBER:
            return _NUMBER
        case FieldKind.BOOLEAN:
            return _BOOLEAN
        case FieldKind.STRING:
            return string
        case FieldKind.ANY:
            return fallback if fallback is not None else one_or_more(LINE_CHAR)


def quoted_string(excluded: str, *, non_empty: bool) -> Node:
    """A double-quoted string whose characters exclude ``excluded`` (and the quote itself)."""
    char = CharSet(chars='"' + excluded, negated=True)
    return seq('"', one_or_more(char) if non_empty else zero_or_more(char), '"')
