"""Syntax resolution utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hother.streamblocks.syntaxes.base import BaseSyntax
    from hother.streamblocks.syntaxes.models import Syntax


def resolve_syntax(
    syntax: BaseSyntax | Syntax | None,
    fallback: BaseSyntax | Syntax | None = None,
) -> BaseSyntax | Syntax:
    """Resolve syntax using priority: provided > global > fallback > system default.

    Resolution order:
    1. Provided syntax argument (if not None)
    2. Global default from config (if set)
    3. Fallback argument (if provided)
    4. System default: from DEFAULT_SYNTAX constant

    Args:
        syntax: Explicit syntax to use (highest priority)
        fallback: Fallback syntax if no explicit or global default

    Returns:
        Resolved syntax (enum member or BaseSyntax instance)

    Example:
        >>> from hother.streamblocks.syntaxes.utils import resolve_syntax
        >>> from hother.streamblocks.syntaxes.models import Syntax
        >>> # Uses global or system default
        >>> syntax = resolve_syntax(None)
        >>> # Uses provided syntax
        >>> syntax = resolve_syntax(Syntax.MARKDOWN_FRONTMATTER)
    """
    # 1. Explicit argument takes priority
    if syntax is not None:
        return syntax

    # 2. Check global configuration
    from hother.streamblocks.syntaxes.config import get_default_syntax

    global_default = get_default_syntax()
    if global_default is not None:
        return global_default

    # 3. Use fallback if provided
    if fallback is not None:
        return fallback

    # 4. Fall back to system default constant
    from hother.streamblocks.syntaxes.config import DEFAULT_SYNTAX
    from hother.streamblocks.syntaxes.models import Syntax

    return Syntax[DEFAULT_SYNTAX]
