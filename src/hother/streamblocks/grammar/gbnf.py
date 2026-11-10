"""Render a grammar as GBNF, the grammar format of llama.cpp and compatible servers."""

from __future__ import annotations

import re

from hother.streamblocks.grammar.nodes import ROOT_RULE, CharSet, Choice, Grammar, Literal, Node, Ref, Repeat, Sequence

_LITERAL_ESCAPES = {"\\": "\\\\", '"': '\\"', "\n": "\\n", "\r": "\\r", "\t": "\\t"}
_CHARSET_ESCAPES = {"\\": "\\\\", "]": "\\]", "^": "\\^", "-": "\\-", "\n": "\\n", "\r": "\\r", "\t": "\\t"}
_INVALID_RULE_NAME_CHARS = re.compile(r"[^A-Za-z0-9-]")
_OPTIONAL = (0, 1)
_ZERO_OR_MORE = (0, None)
_ONE_OR_MORE = (1, None)


def rule_name(name: str) -> str:
    """Turn any name into a valid GBNF rule name (letters, digits and dashes)."""
    return _INVALID_RULE_NAME_CHARS.sub("-", name)


def render_gbnf(grammar: Grammar) -> str:
    """Render ``grammar`` as GBNF text, root rule first."""
    names = [ROOT_RULE, *(name for name in grammar.rules if name != ROOT_RULE)]
    return "\n".join(f"{rule_name(name)} ::= {_render(grammar.rules[name])}" for name in names) + "\n"


def _escape(text: str, escapes: dict[str, str]) -> str:
    return "".join(escapes.get(char, char) for char in text)


def _render(node: Node) -> str:
    match node:
        case Literal(text=text):
            return f'"{_escape(text, _LITERAL_ESCAPES)}"'
        case CharSet(chars=chars, ranges=ranges, negated=negated):
            body = _escape(chars, _CHARSET_ESCAPES) + "".join(
                f"{_escape(low, _CHARSET_ESCAPES)}-{_escape(high, _CHARSET_ESCAPES)}" for low, high in ranges
            )
            return f"[{'^' if negated else ''}{body}]"
        case Sequence(items=items):
            return " ".join(_render_operand(item) for item in items) if items else '""'
        case Choice(options=options):
            return " | ".join(_render(option) for option in options)
        case Repeat(item=item, minimum=minimum, maximum=maximum):
            return f"{_render_operand(item, repeated=True)}{_quantifier(minimum, maximum)}"
        case Ref(name=name):  # pragma: no branch - the match is exhaustive
            return rule_name(name)


def _render_operand(node: Node, *, repeated: bool = False) -> str:
    """Render a node used inside a sequence or under a quantifier, with parentheses when needed."""
    rendered = _render(node)
    needs_group = isinstance(node, Choice) or (repeated and isinstance(node, Sequence | Repeat))
    return f"({rendered})" if needs_group else rendered


def _quantifier(minimum: int, maximum: int | None) -> str:
    bounds = (minimum, maximum)
    if bounds == _OPTIONAL:
        return "?"
    if bounds == _ZERO_OR_MORE:
        return "*"
    if bounds == _ONE_OR_MORE:
        return "+"
    return f"{{{minimum},{'' if maximum is None else maximum}}}"
