"""Factory function for creating syntax instances."""

from __future__ import annotations

from enum import StrEnum, auto

from hother.streamblocks.syntaxes.base import BaseSyntax
from hother.streamblocks.syntaxes.delimiter import (
    DelimiterFrontmatterSyntax,
    DelimiterPreambleSyntax,
)
from hother.streamblocks.syntaxes.markdown import MarkdownFrontmatterSyntax


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
    if isinstance(syntax, Syntax):
        match syntax:
            case Syntax.DELIMITER_FRONTMATTER:
                return DelimiterFrontmatterSyntax()
            case Syntax.DELIMITER_PREAMBLE:
                return DelimiterPreambleSyntax()
            case Syntax.MARKDOWN_FRONTMATTER:
                return MarkdownFrontmatterSyntax()
            case _:  # pragma: no cover - guard for future enum additions
                error_msg = f"Unhandled Syntax enum value: {syntax}"
                raise NotImplementedError(error_msg)

    # It's a custom syntax instance - must inherit from BaseSyntax
    if isinstance(syntax, BaseSyntax):
        return syntax

    error_msg = f"Expected Syntax enum or BaseSyntax instance, got {type(syntax).__name__}"
    raise TypeError(error_msg)
