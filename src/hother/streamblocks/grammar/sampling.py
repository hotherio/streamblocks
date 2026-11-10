"""Draw random strings from a grammar, to test that a parser accepts what the grammar allows."""

from __future__ import annotations

import string
from typing import TYPE_CHECKING

from hother.streamblocks.grammar.nodes import ROOT_RULE, CharSet, Choice, Grammar, Literal, Node, Ref, Repeat, Sequence

if TYPE_CHECKING:
    from random import Random

# Characters used when a negated set leaves the choice open
_ALPHABET = string.ascii_letters + string.digits + string.punctuation + " \t\n" + "éß→"

# Extra repetitions drawn for an unbounded repeat
_MAX_EXTRA_REPEATS = 3


def sample(grammar: Grammar, rng: Random, *, rule: str = ROOT_RULE) -> str:
    """Return one random string matched by ``rule`` of ``grammar``."""
    return _sample(grammar.rules[rule], grammar, rng)


def _sample(node: Node, grammar: Grammar, rng: Random) -> str:
    match node:
        case Literal(text=text):
            return text
        case CharSet():
            return rng.choice(_candidates(node))
        case Sequence(items=items):
            return "".join(_sample(item, grammar, rng) for item in items)
        case Choice(options=options):
            return _sample(rng.choice(options), grammar, rng)
        case Repeat(item=item, minimum=minimum, maximum=maximum):
            upper = minimum + _MAX_EXTRA_REPEATS if maximum is None else maximum
            return "".join(_sample(item, grammar, rng) for _ in range(rng.randint(minimum, upper)))
        case Ref(name=name):
            return _sample(grammar.rules[name], grammar, rng)


def _candidates(charset: CharSet) -> str:
    """Characters a set can produce, limited to the sampling alphabet when negated."""
    members = charset.chars + "".join(
        chr(code) for low, high in charset.ranges for code in range(ord(low), ord(high) + 1)
    )
    if not charset.negated:
        return members
    return "".join(char for char in _ALPHABET if char not in members)
