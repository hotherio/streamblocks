"""Global syntax configuration for StreamBlocks."""

from __future__ import annotations

from threading import Lock
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hother.streamblocks.syntaxes.base import BaseSyntax
    from hother.streamblocks.syntaxes.models import Syntax

# System default syntax
DEFAULT_SYNTAX: str = "DELIMITER_FRONTMATTER"  # Syntax enum member name

# Global state
_default_syntax: BaseSyntax | Syntax | None = None
_lock = Lock()


def set_default_syntax(syntax: BaseSyntax | Syntax) -> None:
    """Set the global default syntax for all StreamBlocks operations.

    Once set, this syntax will be used automatically for all operations
    that accept an optional syntax parameter (from_syntax, to_prompt, etc.).

    Args:
        syntax: Syntax to use as default (enum member or BaseSyntax instance)

    Example:
        >>> import streamblocks as sb
        >>> # Set global default
        >>> sb.set_default_syntax(sb.Syntax.DELIMITER_FRONTMATTER)
        >>> # Now all operations use this syntax by default
        >>> block = FileOperations.from_syntax(text)  # Uses DELIMITER_FRONTMATTER
        >>> registry = sb.Registry()  # Uses DELIMITER_FRONTMATTER
    """
    global _default_syntax
    with _lock:
        _default_syntax = syntax


def get_default_syntax() -> BaseSyntax | Syntax | None:
    """Get the current global default syntax.

    Returns:
        The configured default syntax, or None if not set

    Example:
        >>> import streamblocks as sb
        >>> sb.set_default_syntax(sb.Syntax.MARKDOWN_FRONTMATTER)
        >>> current = sb.get_default_syntax()
        >>> print(current)  # Syntax.MARKDOWN_FRONTMATTER
    """
    with _lock:
        return _default_syntax


def reset_default_syntax() -> None:
    """Reset to system default (DelimiterFrontmatterSyntax).

    This clears any user-configured default, causing the system
    to fall back to the DEFAULT_SYNTAX constant.

    Example:
        >>> import streamblocks as sb
        >>> sb.set_default_syntax(sb.Syntax.MARKDOWN_FRONTMATTER)
        >>> sb.reset_default_syntax()
        >>> # Now uses system default again (DELIMITER_FRONTMATTER)
    """
    global _default_syntax
    with _lock:
        _default_syntax = None
