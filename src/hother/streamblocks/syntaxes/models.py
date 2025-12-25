"""Base syntax class and utilities for StreamBlocks syntax implementations."""

from __future__ import annotations

# Re-export Syntax and get_syntax_instance from factory for backward compatibility
from hother.streamblocks.syntaxes.factory import Syntax, get_syntax_instance

__all__ = ["Syntax", "get_syntax_instance"]
