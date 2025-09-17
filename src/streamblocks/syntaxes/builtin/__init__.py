"""Built-in syntax implementations for streamblocks.

This module provides generic, ready-to-use syntax parsers for common block formats:

- DelimiterPreambleSyntax: Delimiter blocks with inline metadata (!!id:type...)
- MarkdownFrontmatterSyntax: Markdown fence blocks with YAML frontmatter (```...---...---)
- DelimiterFrontmatterSyntax: Delimiter blocks with YAML frontmatter (!!start...---...---...!!end)
"""

from streamblocks.syntaxes.builtin.delimiter import DelimiterPreambleSyntax
from streamblocks.syntaxes.builtin.markdown import MarkdownFrontmatterSyntax
from streamblocks.syntaxes.builtin.yaml_frontmatter import DelimiterFrontmatterSyntax

__all__ = [
    "DelimiterPreambleSyntax",
    "MarkdownFrontmatterSyntax",
    "DelimiterFrontmatterSyntax",
]
