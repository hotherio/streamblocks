"""Shared utility functions for StreamBlocks core."""

from __future__ import annotations

from typing import Any

import yaml


def load_yaml(text: str) -> Any:
    """``yaml.safe_load`` using the libyaml C loader when available."""
    if yaml.__with_libyaml__:
        return yaml.load(text, Loader=yaml.CSafeLoader)
    return yaml.safe_load(text)


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
