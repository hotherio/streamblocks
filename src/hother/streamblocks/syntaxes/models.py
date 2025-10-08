"""Base syntax class and utilities for StreamBlocks syntax implementations."""

from __future__ import annotations

from enum import StrEnum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import BaseSyntax


class Syntax(StrEnum):
    """Enum of built-in syntax types."""

    DELIMITER_FRONTMATTER = auto()
    DELIMITER_PREAMBLE = auto()
    MARKDOWN_FRONTMATTER = auto()


def get_syntax_instance(
    syntax: Syntax | BaseSyntax,
) -> BaseSyntax:
    """Get a syntax instance from a Syntax enum or return custom instance.

    This helper function allows users to specify built-in syntaxes using
    the Syntax enum or provide their own custom syntax implementations.

    Args:
        syntax: Either a Syntax enum member or a custom BaseSyntax instance

    Returns:
        A syntax instance inheriting from BaseSyntax

    Raises:
        TypeError: If syntax is neither a Syntax enum nor a BaseSyntax instance

    Example:
        >>> # Using built-in syntax
        >>> syntax = get_syntax_instance(Syntax.DELIMITER_PREAMBLE)
        >>>
        >>> # Using custom syntax
        >>> my_syntax = MySyntax()
        >>> syntax = get_syntax_instance(my_syntax)
    """
    # Import here to avoid circular imports
    from hother.streamblocks.syntaxes.delimiter import (  # noqa: PLC0415
        DelimiterFrontmatterSyntax,
        DelimiterPreambleSyntax,
    )
    from hother.streamblocks.syntaxes.markdown import MarkdownFrontmatterSyntax  # noqa: PLC0415

    if isinstance(syntax, Syntax):
        match syntax:
            case Syntax.DELIMITER_FRONTMATTER:
                return DelimiterFrontmatterSyntax()
            case Syntax.DELIMITER_PREAMBLE:
                return DelimiterPreambleSyntax()
            case Syntax.MARKDOWN_FRONTMATTER:
                return MarkdownFrontmatterSyntax()

    # It's a custom syntax instance
    if hasattr(syntax, "detect_line") and hasattr(syntax, "parse_block"):
        return syntax

    error_msg = f"Expected Syntax enum or BaseSyntax instance, got {type(syntax)}"
    raise TypeError(error_msg)
