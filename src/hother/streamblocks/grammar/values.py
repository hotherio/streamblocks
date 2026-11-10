"""Grammar nodes for metadata values, shared by the built-in syntaxes."""

from __future__ import annotations

from typing import TYPE_CHECKING

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

if TYPE_CHECKING:
    from collections.abc import Sequence

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
        case FieldKind.ANY:  # pragma: no branch - the match is exhaustive
            return fallback if fallback is not None else one_or_more(LINE_CHAR)


def quoted_string(excluded: str, *, non_empty: bool) -> Node:
    """A double-quoted string whose characters exclude ``excluded`` (and the quote itself)."""
    char = CharSet(chars='"' + excluded, negated=True)
    return seq('"', one_or_more(char) if non_empty else zero_or_more(char), '"')


def without(charset: CharSet, chars: str) -> CharSet:
    """``charset`` minus ``chars``."""
    if charset.negated:
        return CharSet(chars=charset.chars + chars, ranges=charset.ranges, negated=True)
    members = charset.chars + "".join(
        chr(code) for low, high in charset.ranges for code in range(ord(low), ord(high) + 1)
    )
    return CharSet(chars="".join(char for char in members if char not in chars))


def word_not_in(words: Sequence[str], *, first: CharSet, rest: CharSet, space: CharSet | None = None) -> Node:
    """A non-empty value that is none of ``words``.

    The value starts with a character of ``first`` and continues with
    characters of ``rest``. With ``space``, the value may also contain those
    characters but never ends with one (trailing spaces would be stripped and
    could turn the value back into one of the words).

    Args:
        words: Values to exclude, compared in full (not as prefixes)
        first: Allowed first character
        rest: Allowed following characters, spaces excluded
        space: Allowed inner space characters, if any
    """
    tail = zero_or_more(rest) if space is None else zero_or_more(seq(zero_or_more(space), rest))

    def after(prefixes: tuple[str, ...], allowed: CharSet, *, may_stop: bool) -> Node:
        heads = "".join(dict.fromkeys(prefix[0] for prefix in prefixes if prefix))
        options: list[Node] = [seq(without(allowed, heads), tail)]
        if space is not None and allowed is rest:
            options.append(seq(one_or_more(space), rest, tail))
        for head in heads:
            tails = tuple(prefix[1:] for prefix in prefixes if prefix and prefix[0] == head)
            options.append(seq(head, after(tails, rest, may_stop="" not in tails)))
        body = choice(*options)
        return optional(body) if may_stop else body

    return after(tuple(words), first, may_stop=False)
