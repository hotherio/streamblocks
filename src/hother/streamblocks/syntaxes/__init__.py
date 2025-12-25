"""Built-in syntax implementations for StreamBlocks."""

from hother.streamblocks.syntaxes.base import BaseSyntax
from hother.streamblocks.syntaxes.delimiter import (
    DelimiterFrontmatterSyntax,
    DelimiterPreambleSyntax,
)
from hother.streamblocks.syntaxes.factory import get_syntax_instance
from hother.streamblocks.syntaxes.markdown import MarkdownFrontmatterSyntax
from hother.streamblocks.syntaxes.models import Syntax

__all__ = [
    "BaseSyntax",
    "DelimiterFrontmatterSyntax",
    "DelimiterPreambleSyntax",
    "MarkdownFrontmatterSyntax",
    "Syntax",
    "get_syntax_instance",
]
