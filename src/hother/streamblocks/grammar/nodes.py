"""Grammar building blocks, independent of any grammar dialect.

A grammar is a set of named rules. Each rule is a tree of nodes: literals,
character sets, sequences, alternatives, repetitions and references to other
rules. Renderers turn a :class:`Grammar` into a concrete dialect such as GBNF.
"""

from __future__ import annotations

from dataclasses import dataclass, field

NEWLINE = "\n"
ROOT_RULE = "root"


@dataclass(frozen=True, slots=True)
class Literal:
    """An exact string."""

    text: str


@dataclass(frozen=True, slots=True)
class CharSet:
    """One character taken from (or, when negated, outside) a set.

    Attributes:
        chars: Individual characters in the set
        ranges: Inclusive ``(low, high)`` character ranges in the set
        negated: Match any character that is *not* in the set
    """

    chars: str = ""
    ranges: tuple[tuple[str, str], ...] = ()
    negated: bool = False


@dataclass(frozen=True, slots=True)
class Sequence:
    """Nodes that follow one another."""

    items: tuple[Node, ...]


@dataclass(frozen=True, slots=True)
class Choice:
    """Exactly one of several nodes."""

    options: tuple[Node, ...]


@dataclass(frozen=True, slots=True)
class Repeat:
    """A node repeated between ``minimum`` and ``maximum`` times (None means unbounded)."""

    item: Node
    minimum: int = 0
    maximum: int | None = None


@dataclass(frozen=True, slots=True)
class Ref:
    """A reference to a named rule."""

    name: str


type Node = Literal | CharSet | Sequence | Choice | Repeat | Ref


@dataclass(slots=True)
class Grammar:
    """Named rules, starting from :data:`ROOT_RULE`."""

    rules: dict[str, Node] = field(default_factory=dict[str, Node])


def seq(*items: Node | str) -> Sequence:
    """Build a sequence; plain strings become literals."""
    return Sequence(tuple(Literal(item) if isinstance(item, str) else item for item in items))


def choice(*options: Node | str) -> Choice:
    """Build a choice; plain strings become literals."""
    return Choice(tuple(Literal(option) if isinstance(option, str) else option for option in options))


def optional(item: Node) -> Repeat:
    """Zero or one occurrence."""
    return Repeat(item, 0, 1)


def zero_or_more(item: Node) -> Repeat:
    """Any number of occurrences."""
    return Repeat(item)


def one_or_more(item: Node) -> Repeat:
    """At least one occurrence."""
    return Repeat(item, 1)


LINE_CHAR = CharSet(chars=NEWLINE, negated=True)
"""Any character except a line break."""

REST_OF_LINE = zero_or_more(LINE_CHAR)
"""The remainder of a line, without its line break."""

INLINE_SPACE = CharSet(chars=" \t")
"""A space or a tab."""


def line_not_starting_with(*prefixes: str, non_blank: bool = False) -> Node:
    """A full line (with its line break) that does not start with any of ``prefixes``.

    Leading spaces and tabs are skipped before the comparison, so an indented
    marker is excluded too. This is how free text and block content are kept
    from being mistaken for an opening or closing marker.

    Args:
        *prefixes: Non-empty strings the line must not start with
        non_blank: Also require at least one character other than spaces and tabs
    """
    return seq(zero_or_more(INLINE_SPACE), _avoid(tuple(prefixes), first=True, non_blank=non_blank), NEWLINE)


def _avoid(prefixes: tuple[str, ...], *, first: bool = False, non_blank: bool = False) -> Node:
    """What may follow, given that the text so far is a proper prefix of each of ``prefixes``."""
    heads = "".join(dict.fromkeys(prefix[0] for prefix in prefixes))
    # Leading whitespace was already consumed, so the first character is not a space or a tab
    excluded = heads + NEWLINE + (INLINE_SPACE.chars if first else "")
    options: list[Node] = [seq(CharSet(chars=excluded, negated=True), REST_OF_LINE)]
    for head in heads:
        tails = tuple(prefix[1:] for prefix in prefixes if prefix[0] == head)
        if all(tails):
            options.append(seq(head, _avoid(tails)))
    rest = Choice(tuple(options))
    # Stopping here is fine too: the line is then blank, or a proper prefix of a marker
    return rest if non_blank else optional(rest)


class SharedLines:
    """Content-line rules for a syntax, defined once and referred to by name.

    Calling the instance returns a reference to a rule matching a full line
    that starts with none of the syntax ``markers`` nor the extra prefixes.
    The rules themselves accumulate in :attr:`rules`.
    """

    def __init__(self, *markers: str, name: str = "line") -> None:
        """Create a factory for lines that avoid ``markers``."""
        self._markers = markers
        self._name = name
        self._names: dict[tuple[tuple[str, ...], bool], str] = {}
        self.rules: dict[str, Node] = {}

    def __call__(self, *prefixes: str, non_blank: bool = False) -> Node:
        """Return a reference to the line rule avoiding the markers and ``prefixes``."""
        key = (prefixes, non_blank)
        if key not in self._names:
            rule = f"{self._name}-{len(self._names)}" if self._names else self._name
            self._names[key] = rule
            self.rules[rule] = line_not_starting_with(*self._markers, *prefixes, non_blank=non_blank)
        return Ref(self._names[key])
