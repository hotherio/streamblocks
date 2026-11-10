"""Grammars for constrained decoding, generated from a registry.

A grammar makes a local model's output well-formed by construction: the
decoder can only produce text that the registry's syntax and block types
accept. Use :meth:`hother.streamblocks.Registry.to_grammar` for the common
case.
"""

from hother.streamblocks.grammar.compiler import GBNF, build_grammar, compile_grammar
from hother.streamblocks.grammar.gbnf import render_gbnf
from hother.streamblocks.grammar.matching import accepts
from hother.streamblocks.grammar.nodes import Grammar
from hother.streamblocks.grammar.sampling import sample
from hother.streamblocks.grammar.spec import (
    BlockSpec,
    FieldKind,
    GrammarError,
    LineFactory,
    MetadataField,
    SyntaxGrammar,
)

__all__ = [
    "GBNF",
    "BlockSpec",
    "FieldKind",
    "Grammar",
    "GrammarError",
    "LineFactory",
    "MetadataField",
    "SyntaxGrammar",
    "accepts",
    "build_grammar",
    "compile_grammar",
    "render_gbnf",
    "sample",
]
