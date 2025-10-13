"""Built-in syntax implementations for StreamBlocks."""

from hother.streamblocks.syntaxes.base import BaseSyntax
from hother.streamblocks.syntaxes.config import (
    DEFAULT_SYNTAX,
    get_default_syntax,
    reset_default_syntax,
    set_default_syntax,
)
from hother.streamblocks.syntaxes.delimiter import (
    DelimiterFrontmatterSyntax,
    DelimiterPreambleSyntax,
)
from hother.streamblocks.syntaxes.markdown import MarkdownFrontmatterSyntax
from hother.streamblocks.syntaxes.models import Syntax

__all__ = [
    "BaseSyntax",
    "DEFAULT_SYNTAX",
    "DelimiterFrontmatterSyntax",
    "DelimiterPreambleSyntax",
    "MarkdownFrontmatterSyntax",
    "Syntax",
    "get_default_syntax",
    "reset_default_syntax",
    "set_default_syntax",
]
