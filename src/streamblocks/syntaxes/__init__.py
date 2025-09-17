"""Syntax framework for StreamBlocks.

This module provides the base classes and utilities for implementing
block syntax parsers. It includes:

- BlockSyntax protocol (re-exported from core.types)
- Abstract base classes for common syntax patterns
- Utility functions for pattern matching and parsing
- Built-in syntax implementations
- Mock implementations for testing

The syntax framework is designed to be extensible, allowing users
to create custom syntaxes while providing common functionality
through base classes.
"""

from streamblocks.core.types import (
    BlockState,
    BlockSyntax,
    DetectionResult,
    ParseResult,
)
from streamblocks.syntaxes.abc import BaseSyntax, DelimiterSyntax, FrontmatterSyntax
from streamblocks.syntaxes.builtin import (
    DelimiterBlockSyntax,
    MarkdownCodeSyntax,
    YAMLFrontmatterSyntax,
)
from streamblocks.syntaxes.utils import (
    build_delimiter_pattern,
    dedent,
    escape_delimiter,
    extract_key_value_pairs,
    indent_text,
    match_pattern,
    parse_inline_metadata,
    parse_to_model,
    parse_yaml_metadata,
    safe_get_nested,
    strip_markers,
    validate_yaml_format,
)

__all__ = [
    # Protocol and types
    "BlockSyntax",
    "BlockState",
    "DetectionResult",
    "ParseResult",
    # Base classes
    "BaseSyntax",
    "FrontmatterSyntax",
    "DelimiterSyntax",
    # Built-in syntaxes
    "YAMLFrontmatterSyntax",
    "DelimiterBlockSyntax",
    "MarkdownCodeSyntax",
    # Pattern helpers
    "escape_delimiter",
    "build_delimiter_pattern",
    "match_pattern",
    # Metadata parsing
    "parse_inline_metadata",
    "parse_yaml_metadata",
    "extract_key_value_pairs",
    # Content processing
    "strip_markers",
    "validate_yaml_format",
    "indent_text",
    "dedent",
    # Model helpers
    "parse_to_model",
    "safe_get_nested",
]
