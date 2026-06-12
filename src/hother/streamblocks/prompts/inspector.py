"""Introspection helpers that turn block classes into prompt fragments."""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from hother.streamblocks.core.types import BaseContent

_DEFAULT_PARSE_MARKER = "Default parse method that just stores raw content"
_DOCSTRING_SECTION_HEADERS = ("args:", "returns:", "raises:", "example:", "examples:")
_USAGE_PREFIX = "usage:"
_USAGE_KEYWORDS = ("use this", "use when", "for ")
_JSON_FORMAT = "json"
_YAML_FORMAT = "yaml"


def parse_block_docstring(block_class: type) -> tuple[str, str | None]:
    """Split a block class docstring into (description, usage).

    The first paragraph is the description. Usage is taken from a paragraph
    starting with "Usage:" or "Use this", falling back to the second paragraph
    when it reads like usage guidance.
    """
    docstring = inspect.getdoc(block_class)
    if not docstring:
        return "", None

    paragraphs = _split_paragraphs(docstring)
    return paragraphs[0], _find_usage(paragraphs)


def _split_paragraphs(text: str) -> list[str]:
    """Collapse a docstring into blank-line-separated paragraphs."""
    paragraphs: list[str] = []
    current: list[str] = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped:
            current.append(stripped)
        elif current:
            paragraphs.append(" ".join(current))
            current = []
    if current:
        paragraphs.append(" ".join(current))
    return paragraphs


def _find_usage(paragraphs: list[str]) -> str | None:
    """Locate the usage paragraph among non-leading paragraphs."""
    for paragraph in paragraphs[1:]:
        lowered = paragraph.lower()
        if lowered.startswith(_USAGE_PREFIX):
            return paragraph[len(_USAGE_PREFIX) :].strip()
        if lowered.startswith("use this"):
            return paragraph

    if len(paragraphs) > 1:
        second = paragraphs[1]
        if any(keyword in second.lower() for keyword in _USAGE_KEYWORDS):
            return second
    return None


def inspect_content_format(content_class: type[BaseContent]) -> str | None:
    """Describe a content class's expected format for prompts.

    Uses the ``__content_format__`` marker set by ``@parse_as_json`` /
    ``@parse_as_yaml`` when present, otherwise the docstring of a custom
    ``parse()`` method. Returns None when no format guidance is available.
    """
    content_format = getattr(content_class, "__content_format__", None)
    if content_format in (_JSON_FORMAT, _YAML_FORMAT):
        return _describe_serialized_format(content_class, content_format)
    return _describe_custom_parse(content_class)


def _describe_custom_parse(content_class: type[BaseContent]) -> str | None:
    """Extract the description part of a custom parse() docstring, if any."""
    docstring = inspect.getdoc(content_class.parse)
    if not docstring or _DEFAULT_PARSE_MARKER in docstring:
        return None

    description_lines: list[str] = []
    for line in docstring.split("\n"):
        if line.strip().lower().startswith(_DOCSTRING_SECTION_HEADERS):
            break
        description_lines.append(line)

    description = "\n".join(description_lines).strip()
    return description or None


def _describe_serialized_format(content_class: type[BaseContent], content_format: str) -> str:
    """Render a JSON/YAML structure hint from a content class's fields."""
    fields = [(name, info) for name, info in content_class.model_fields.items() if name != "raw_content"]
    if not fields:
        return f"Content should be valid {content_format.upper()}"

    lines = [f"Content should be valid {content_format.upper()} with the following structure:", ""]
    if content_format == _JSON_FORMAT:
        lines.append("{")
        last_index = len(fields) - 1
        for index, (name, info) in enumerate(fields):
            comma = "," if index < last_index else ""
            suffix = f"  // {info.description}" if info.description else ""
            lines.append(f'  "{name}": {_format_type_hint(info.annotation)}{comma}{suffix}')
        lines.append("}")
    else:
        for name, info in fields:
            suffix = f"  # {info.description}" if info.description else ""
            lines.append(f"{name}: {_format_type_hint(info.annotation)}{suffix}")
    return "\n".join(lines)


# Ordered (substring, placeholder) pairs. Containers come before scalars
# because e.g. "list[str]" contains the substring "str".
_TYPE_PLACEHOLDERS: tuple[tuple[str, str], ...] = (
    ("list", "[...]"),
    ("dict", "{...}"),
    ("bool", "true/false"),
    ("int", "123"),
    ("float", "1.23"),
    ("str", '"string"'),
)


def _format_type_hint(annotation: Any) -> str:
    """Render a type annotation as a short example placeholder."""
    if annotation is None:
        return "any"

    lowered = str(annotation).lower().replace("typing.", "").replace("<class '", "").replace("'>", "")
    for needle, placeholder in _TYPE_PLACEHOLDERS:
        if needle in lowered:
            return placeholder
    return "..."
