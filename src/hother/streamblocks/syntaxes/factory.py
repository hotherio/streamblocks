"""Factory function for creating syntax instances."""

from __future__ import annotations

from enum import StrEnum, auto
from typing import cast

from hother.streamblocks.core.exceptions import SyntaxConfigError
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
        SyntaxConfigError: If syntax is neither a Syntax enum nor a BaseSyntax instance

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

    # A custom instance must inherit from BaseSyntax. Validate against ``object``
    # rather than the declared type: callers may be untyped and pass an
    # unsupported value (or a future, unhandled Syntax member), which must raise.
    unchecked = cast("object", syntax)
    if isinstance(unchecked, BaseSyntax):
        return unchecked
    raise SyntaxConfigError(received_type=type(unchecked).__name__)
