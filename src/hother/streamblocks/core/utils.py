"""Shared utility functions for StreamBlocks core."""

from __future__ import annotations


def get_syntax_name(syntax: object) -> str:
    """Get the class name of a syntax instance.

    Args:
        syntax: A syntax instance

    Returns:
        The class name as a string

    Example:
        >>> from hother.streamblocks.syntaxes.delimiter import DelimiterPreambleSyntax
        >>> syntax = DelimiterPreambleSyntax()
        >>> get_syntax_name(syntax)
        'DelimiterPreambleSyntax'
    """
    return type(syntax).__name__
