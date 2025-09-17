"""Built-in syntax implementations for streamblocks.

This module provides ready-to-use syntax parsers for common block formats:

- YAMLFrontmatterSyntax: YAML frontmatter blocks (---...---)
- DelimiterBlockSyntax: Delimiter-based blocks (!!block:type...)
- MarkdownCodeSyntax: Markdown code blocks (```language...)
"""

from streamblocks.syntaxes.builtin.delimiter import DelimiterBlockSyntax
from streamblocks.syntaxes.builtin.markdown import MarkdownCodeSyntax
from streamblocks.syntaxes.builtin.yaml_frontmatter import YAMLFrontmatterSyntax

__all__ = [
    "YAMLFrontmatterSyntax",
    "DelimiterBlockSyntax",
    "MarkdownCodeSyntax",
]
