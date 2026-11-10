"""Compile a registry into a grammar for constrained decoding."""

from __future__ import annotations

from typing import TYPE_CHECKING

from hother.streamblocks.grammar.gbnf import render_gbnf
from hother.streamblocks.grammar.nodes import (
    NEWLINE,
    ROOT_RULE,
    Grammar,
    Node,
    Ref,
    choice,
    optional,
    seq,
    without_line_break,
    zero_or_more,
)
from hother.streamblocks.grammar.spec import GrammarError, block_spec

if TYPE_CHECKING:
    from hother.streamblocks.core.registry import Registry

GBNF = "gbnf"
"""GBNF, the grammar format of llama.cpp and compatible servers (LM Studio, ...)."""

_RENDERERS = {GBNF: render_gbnf}

_TEXT_LINE_RULE = "text-line"
_LAST_LINE_RULE = "last-line"
_BLOCK_RULE = "block"
_BLOCK_RULE_PREFIX = "block-"


def build_grammar(registry: Registry, *, allow_text: bool = True, min_blocks: int = 0) -> Grammar:
    """Build the grammar of everything ``registry`` can extract.

    The grammar accepts any number of blocks of the registered types, written
    in the registry's syntax. With ``allow_text`` it also accepts lines of free
    text between them, as long as they cannot be mistaken for a block. The
    output may stop right after a closing marker or a last line of text,
    without a final line break.

    Args:
        registry: Registry holding the syntax and the block types
        allow_text: Allow free text around blocks
        min_blocks: Number of blocks the output must contain at least

    Raises:
        GrammarError: If no block is registered or ``min_blocks`` is negative
        NotImplementedError: If the registry's syntax does not support grammars
    """
    if not registry.registered_blocks:
        msg = "Cannot build a grammar: no block type is registered"
        raise GrammarError(msg)
    if min_blocks < 0:
        msg = f"min_blocks must not be negative, got {min_blocks}"
        raise GrammarError(msg)

    specs = [block_spec(block_type, block_class) for block_type, block_class in registry.registered_blocks.items()]
    syntax_grammar = registry.syntax.grammar_rules(specs)

    grammar = Grammar()
    # A block rule stops before its final line break, so that an answer may end right after a block
    block, text = Ref(_BLOCK_RULE), Ref(_TEXT_LINE_RULE)
    lead: list[Node] = [zero_or_more(text)] if allow_text else []
    item: Node = choice(seq(block, NEWLINE), text) if allow_text else seq(block, NEWLINE)
    ending: Node = optional(choice(block, Ref(_LAST_LINE_RULE)) if allow_text else block)
    if min_blocks:
        required = [seq(*lead, block, NEWLINE)] * (min_blocks - 1)
        root = seq(*required, *lead, block, optional(seq(NEWLINE, zero_or_more(item), ending)))
    else:
        root = seq(zero_or_more(item), ending)
    grammar.rules[ROOT_RULE] = root
    grammar.rules[_BLOCK_RULE] = choice(*(Ref(_BLOCK_RULE_PREFIX + block_type) for block_type in syntax_grammar.blocks))
    for block_type, node in syntax_grammar.blocks.items():
        grammar.rules[_BLOCK_RULE_PREFIX + block_type] = without_line_break(node)
    if allow_text:
        grammar.rules[_TEXT_LINE_RULE] = syntax_grammar.text_line
        grammar.rules[_LAST_LINE_RULE] = without_line_break(syntax_grammar.text_line)
    grammar.rules.update(syntax_grammar.shared)
    return grammar


def compile_grammar(registry: Registry, *, dialect: str = GBNF, allow_text: bool = True, min_blocks: int = 0) -> str:
    """Compile ``registry`` into grammar text in the given dialect.

    Args:
        registry: Registry holding the syntax and the block types
        dialect: Grammar dialect (only ``"gbnf"`` for now)
        allow_text: Allow free text around blocks
        min_blocks: Number of blocks the output must contain at least

    Raises:
        GrammarError: If the dialect is unknown, no block is registered or ``min_blocks`` is negative
        NotImplementedError: If the registry's syntax does not support grammars
    """
    renderer = _RENDERERS.get(dialect)
    if renderer is None:
        msg = f"Unknown grammar dialect {dialect!r}; available: {', '.join(_RENDERERS)}"
        raise GrammarError(msg)
    return renderer(build_grammar(registry, allow_text=allow_text, min_blocks=min_blocks))
