"""Check whether a grammar accepts a given text.

Useful to verify that the examples shown to a model in a prompt are text the
grammar lets it write: a grammar that rejects the style a model naturally
uses pushes it towards unlikely tokens and degrades its output.
"""

from __future__ import annotations

from hother.streamblocks.grammar.nodes import ROOT_RULE, CharSet, Choice, Grammar, Literal, Node, Ref, Repeat, Sequence


def accepts(grammar: Grammar, text: str, *, rule: str = ROOT_RULE) -> bool:
    """Whether ``rule`` of ``grammar`` matches the whole of ``text``."""
    return len(text) in _Matcher(grammar, text).ends(grammar.rules[rule], 0)


class _Matcher:
    """Computes, for a node and a start position, every position a match can end at."""

    def __init__(self, grammar: Grammar, text: str) -> None:
        self._grammar = grammar
        self._text = text
        self._cache: dict[tuple[int, int], frozenset[int]] = {}

    def ends(self, node: Node, start: int) -> frozenset[int]:
        key = (id(node), start)
        if key not in self._cache:
            self._cache[key] = frozenset(self._ends(node, start))
        return self._cache[key]

    def _ends(self, node: Node, start: int) -> set[int]:
        text = self._text
        match node:
            case Literal(text=literal):
                return {start + len(literal)} if text.startswith(literal, start) else set()
            case CharSet():
                return {start + 1} if start < len(text) and _contains(node, text[start]) else set()
            case Sequence(items=items):
                positions = {start}
                for item in items:
                    positions = {end for position in positions for end in self.ends(item, position)}
                return positions
            case Choice(options=options):
                return {end for option in options for end in self.ends(option, start)}
            case Repeat():
                return self._repeat(node, start)
            case Ref(name=name):  # pragma: no branch - the match is exhaustive
                return set(self.ends(self._grammar.rules[name], start))

    def _repeat(self, node: Repeat, start: int) -> set[int]:
        results = {start} if node.minimum == 0 else set[int]()
        frontier = {start}
        count = 0
        while frontier and (node.maximum is None or count < node.maximum):
            count += 1
            reached = {end for position in frontier for end in self.ends(node.item, position)}
            # Only positions that make progress are explored again, so empty matches cannot loop
            frontier = reached - results if count >= node.minimum else reached
            if count >= node.minimum:
                results |= reached
            if node.maximum is None and count > len(self._text) + node.minimum:
                break
        return results


def _contains(charset: CharSet, char: str) -> bool:
    member = char in charset.chars or any(low <= char <= high for low, high in charset.ranges)
    return member != charset.negated
