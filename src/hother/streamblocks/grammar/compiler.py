"""Compile a registry into a grammar for constrained decoding."""

from __future__ import annotations

from typing import TYPE_CHECKING

from hother.streamblocks.grammar.gbnf import render_gbnf
from hother.streamblocks.grammar.nodes import ROOT_RULE, Grammar, Ref, choice, zero_or_more
from hother.streamblocks.grammar.spec import GrammarError, block_spec

if TYPE_CHECKING:
    from hother.streamblocks.core.registry import Registry

GBNF = "gbnf"
"""GBNF, the grammar format of llama.cpp and compatible servers (LM Studio, ...)."""

_RENDERERS = {GBNF: render_gbnf}

_TEXT_LINE_RULE = "text-line"
_BLOCK_RULE = "block"
_BLOCK_RULE_PREFIX = "block-"


def build_grammar(registry: Registry, *, allow_text: bool = True) -> Grammar:
    """Build the grammar of everything ``registry`` can extract.

    The grammar accepts any number of blocks of the registered types, written
    in the registry's syntax. With ``allow_text`` it also accepts lines of free
    text between them, as long as they cannot be mistaken for a block.

    Args:
        registry: Registry holding the syntax and the block types
        allow_text: Allow free text around blocks

    Raises:
        GrammarError: If no block is registered
        NotImplementedError: If the registry's syntax does not support grammars
    """
    if not registry.registered_blocks:
        msg = "Cannot build a grammar: no block type is registered"
        raise GrammarError(msg)

    specs = [block_spec(block_type, block_class) for block_type, block_class in registry.registered_blocks.items()]
    syntax_grammar = registry.syntax.grammar_rules(specs)

    grammar = Grammar()
    alternatives = [Ref(_BLOCK_RULE), Ref(_TEXT_LINE_RULE)]
    grammar.rules[ROOT_RULE] = zero_or_more(choice(*alternatives) if allow_text else Ref(_BLOCK_RULE))
    grammar.rules[_BLOCK_RULE] = choice(*(Ref(_BLOCK_RULE_PREFIX + block_type) for block_type in syntax_grammar.blocks))
    for block_type, node in syntax_grammar.blocks.items():
        grammar.rules[_BLOCK_RULE_PREFIX + block_type] = node
    if allow_text:
        grammar.rules[_TEXT_LINE_RULE] = syntax_grammar.text_line
    grammar.rules.update(syntax_grammar.shared)
    return grammar


def compile_grammar(registry: Registry, *, dialect: str = GBNF, allow_text: bool = True) -> str:
    """Compile ``registry`` into grammar text in the given dialect.

    Args:
        registry: Registry holding the syntax and the block types
        dialect: Grammar dialect (only ``"gbnf"`` for now)
        allow_text: Allow free text around blocks

    Raises:
        GrammarError: If the dialect is unknown or no block is registered
        NotImplementedError: If the registry's syntax does not support grammars
    """
    renderer = _RENDERERS.get(dialect)
    if renderer is None:
        msg = f"Unknown grammar dialect {dialect!r}; available: {', '.join(_RENDERERS)}"
        raise GrammarError(msg)
    return renderer(build_grammar(registry, allow_text=allow_text))
