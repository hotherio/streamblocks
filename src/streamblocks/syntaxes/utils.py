"""Utility functions for syntax parsing.

This module provides common utilities for syntax implementations:

- Pattern building and matching helpers
- Metadata extraction utilities
- Content processing functions
- YAML parsing helpers
"""

from __future__ import annotations

import re
from textwrap import dedent
from typing import Any, cast

import yaml
from pydantic import BaseModel

# Constants
MIN_PARTS_FOR_METADATA = 2

# Pattern Building Helpers


def escape_delimiter(delimiter: str) -> str:
    """Escape a delimiter string for use in regex patterns.

    Args:
        delimiter: The delimiter string to escape

    Returns:
        Regex-escaped delimiter string
    """
    return re.escape(delimiter)


def build_delimiter_pattern(prefix: str, suffix: str | None = None, capture_middle: bool = True) -> str:
    """Build a regex pattern for delimiter-based markers.

    Args:
        prefix: The prefix part of the delimiter
        suffix: Optional suffix part
        capture_middle: Whether to capture content between prefix/suffix

    Returns:
        Regex pattern string

    Examples:
        >>> build_delimiter_pattern("!!", ":end")
        '^!!(.*)(?::end)$'
        >>> build_delimiter_pattern("```", capture_middle=False)
        '^```$'
    """
    escaped_prefix = escape_delimiter(prefix)

    if suffix:
        escaped_suffix = escape_delimiter(suffix)
        if capture_middle:
            return f"^{escaped_prefix}(.*)(?:{escaped_suffix})$"
        return f"^{escaped_prefix}.*{escaped_suffix}$"
    if capture_middle:
        return f"^{escaped_prefix}(.*)$"
    return f"^{escaped_prefix}$"


def match_pattern(pattern: str, line: str) -> re.Match[str] | None:
    """Match a pattern against a line.

    Args:
        pattern: Regex pattern to match
        line: Line to match against

    Returns:
        Match object if successful, None otherwise
    """
    return re.match(pattern, line.strip())


# Metadata Extraction Helpers


def parse_inline_metadata(line: str, delimiter: str = ":") -> dict[str, str]:
    """Parse inline metadata from a delimiter line.

    Args:
        line: Line containing inline metadata (e.g., "!!block123:type:params")
        delimiter: Delimiter separating metadata parts

    Returns:
        Dictionary of parsed metadata

    Examples:
        >>> parse_inline_metadata("!!block123:shell:bash")
        {'id': 'block123', 'type': 'shell', 'params': 'bash'}
    """
    # Remove any prefix markers (like "!!")
    parts = line.strip().split(delimiter)

    if len(parts) < MIN_PARTS_FOR_METADATA:
        return {}

    # Common pattern: first part after prefix is ID
    metadata: dict[str, Any] = {}
    start_idx = 0

    # Try to intelligently parse based on common patterns
    if len(parts) >= MIN_PARTS_FOR_METADATA:
        # Skip the prefix part if it's just markers
        if parts[0].startswith("!!") or parts[0].startswith("```"):
            cleaned = parts[0].lstrip("!").lstrip("`")
            if cleaned:
                metadata["id"] = cleaned
            start_idx = 1
        else:
            metadata["id"] = parts[0]
            start_idx = 1

    # Parse remaining parts
    if len(parts) > start_idx:
        # Common patterns
        if len(parts) == start_idx + 1:
            metadata["type"] = parts[start_idx]
        elif len(parts) == start_idx + 2:
            metadata["type"] = parts[start_idx]
            metadata["params"] = parts[start_idx + 1]
        else:
            # Store all extra parts
            metadata["type"] = parts[start_idx]
            metadata["params"] = delimiter.join(parts[start_idx + 1 :])

    return metadata


def parse_yaml_metadata(yaml_text: str) -> dict[str, Any]:
    """Safely parse YAML metadata.

    Args:
        yaml_text: YAML-formatted text

    Returns:
        Parsed dictionary

    Raises:
        ValueError: If YAML parsing fails
    """
    try:
        # Use safe_load to avoid arbitrary code execution
        data = yaml.safe_load(yaml_text)
        if data is None:
            return {}
        if not isinstance(data, dict):
            raise ValueError(f"Expected dict, got {type(data).__name__}")
        return cast(dict[str, Any], data)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML: {e}") from e


def extract_key_value_pairs(text: str, separator: str = "=", line_delimiter: str = "\n") -> dict[str, str]:
    """Extract key-value pairs from text.

    Args:
        text: Text containing key-value pairs
        separator: Separator between key and value
        line_delimiter: Delimiter between pairs

    Returns:
        Dictionary of key-value pairs

    Examples:
        >>> extract_key_value_pairs("name=test\ntype=shell")
        {'name': 'test', 'type': 'shell'}
    """
    pairs: dict[str, str] = {}
    for line in text.strip().split(line_delimiter):
        line_stripped = line.strip()
        if separator in line_stripped:
            key, value = line_stripped.split(separator, 1)
            pairs[key.strip()] = value.strip()
    return pairs


# Content Processing Helpers


def strip_markers(content: str, prefix: str, suffix: str | None = None) -> str:
    """Strip delimiter markers from content.

    Args:
        content: Content possibly containing markers
        prefix: Prefix marker to remove
        suffix: Optional suffix marker to remove

    Returns:
        Content with markers stripped
    """
    lines = content.split("\n")
    result: list[str] = []

    for line in lines:
        stripped = line.strip()
        # Remove prefix
        if stripped.startswith(prefix):
            continue
        # Remove suffix
        if suffix and stripped.endswith(suffix):
            continue
        result.append(line)

    return "\n".join(result)


def validate_yaml_format(text: str) -> tuple[bool, str | None]:
    """Validate that text is valid YAML.

    Args:
        text: Text to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        yaml.safe_load(text)
        return True, None
    except yaml.YAMLError as e:
        return False, str(e)


def indent_text(text: str, indent: int = 2, indent_char: str = " ") -> str:
    """Indent all lines in text.

    Args:
        text: Text to indent
        indent: Number of indent characters
        indent_char: Character to use for indentation

    Returns:
        Indented text
    """
    prefix = indent_char * indent
    lines = text.split("\n")
    return "\n".join(prefix + line if line else line for line in lines)


# dedent is imported from textwrap module above
# Re-export it for consistency with the module interface
__all__ = ["dedent"]


# Model Parsing Helpers


def parse_to_model[T: BaseModel](model_class: type[T], data: dict[str, Any]) -> T:
    """Parse dictionary data to a Pydantic model.

    Args:
        model_class: The Pydantic model class
        data: Dictionary data to parse

    Returns:
        Instance of the model

    Raises:
        ValueError: If parsing fails
    """
    try:
        return model_class(**data)
    except Exception as e:
        raise ValueError(f"Failed to parse {model_class.__name__}: {e}") from e


def safe_get_nested(data: dict[str, Any], path: str, default: Any = None) -> Any:
    """Safely get nested dictionary values.

    Args:
        data: Dictionary to query
        path: Dot-separated path (e.g., "metadata.type")
        default: Default value if path not found

    Returns:
        Value at path or default

    Examples:
        >>> data = {"metadata": {"type": "shell"}}
        >>> safe_get_nested(data, "metadata.type")
        'shell'
    """
    parts = path.split(".")
    current = data

    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return default

    return current
