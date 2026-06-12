"""Tests for prompt inspector helpers."""

from __future__ import annotations

from typing import Self

import pytest

from hother.streamblocks.core.parsing import parse_as_json, parse_as_yaml
from hother.streamblocks.core.types import BaseContent
from hother.streamblocks.prompts.inspector import (
    _format_type_hint,
    _split_paragraphs,
    inspect_content_format,
    parse_block_docstring,
)


class NoDoc:
    pass


class DescOnly:
    """Just a description."""


class UsagePrefix:
    """A description.

    Usage: do the thing carefully.
    """


class UseThis:
    """A description.

    Use this when you need the thing.
    """


class KeywordFallback:
    """A description.

    For advanced scenarios only.
    """


class SecondNoKeyword:
    """A description.

    Totally unrelated second paragraph.
    """


def test_parse_docstring_none() -> None:
    assert parse_block_docstring(NoDoc) == ("", None)


def test_parse_docstring_description_only() -> None:
    assert parse_block_docstring(DescOnly) == ("Just a description.", None)


def test_parse_docstring_usage_prefix() -> None:
    description, usage = parse_block_docstring(UsagePrefix)
    assert description == "A description."
    assert usage == "do the thing carefully."


def test_parse_docstring_use_this() -> None:
    _, usage = parse_block_docstring(UseThis)
    assert usage == "Use this when you need the thing."


def test_parse_docstring_keyword_fallback() -> None:
    _, usage = parse_block_docstring(KeywordFallback)
    assert usage == "For advanced scenarios only."


def test_parse_docstring_second_without_keyword_has_no_usage() -> None:
    _, usage = parse_block_docstring(SecondNoKeyword)
    assert usage is None


@parse_as_json()
class JsonContent(BaseContent):
    status: int = 0
    label: str = ""


@parse_as_yaml()
class YamlContent(BaseContent):
    name: str = ""


@parse_as_json()
class EmptyJsonContent(BaseContent):
    pass


class CustomParseContent(BaseContent):
    @classmethod
    def parse(cls, raw_text: str) -> Self:
        """Parse the colon separated form.

        Args:
            raw_text: the text.
        """
        return cls(raw_content=raw_text)


class NoDocParseContent(BaseContent):
    @classmethod
    def parse(cls, raw_text: str) -> Self:
        return cls(raw_content=raw_text)


class SectionlessParseContent(BaseContent):
    @classmethod
    def parse(cls, raw_text: str) -> Self:
        """Just a description without sections."""
        return cls(raw_content=raw_text)


def test_split_paragraphs_handles_repeated_and_trailing_blanks() -> None:
    # Repeated blanks (blank while no paragraph buffered) and a trailing blank.
    assert _split_paragraphs("a\n\nb\n\n") == ["a", "b"]


def test_inspect_json_format_lists_fields() -> None:
    result = inspect_content_format(JsonContent)
    assert result is not None
    assert "valid JSON" in result
    assert '"status"' in result
    assert '"label"' in result


def test_inspect_yaml_format() -> None:
    result = inspect_content_format(YamlContent)
    assert result is not None
    assert "valid YAML" in result
    assert "name:" in result


def test_inspect_json_format_no_extra_fields() -> None:
    assert inspect_content_format(EmptyJsonContent) == "Content should be valid JSON"


def test_inspect_custom_parse_docstring() -> None:
    result = inspect_content_format(CustomParseContent)
    assert result == "Parse the colon separated form."


def test_inspect_default_parse_returns_none() -> None:
    assert inspect_content_format(BaseContent) is None


def test_inspect_custom_parse_without_docstring_returns_none() -> None:
    assert inspect_content_format(NoDocParseContent) is None


def test_inspect_custom_parse_without_sections() -> None:
    assert inspect_content_format(SectionlessParseContent) == "Just a description without sections."


@pytest.mark.parametrize(
    ("annotation", "expected"),
    [
        (None, "any"),
        (bool, "true/false"),
        (int, "123"),
        (float, "1.23"),
        (str, '"string"'),
        (list[str], "[...]"),
        (dict[str, int], "{...}"),
        (bytes, "..."),
    ],
)
def test_format_type_hint(annotation: object, expected: str) -> None:
    assert _format_type_hint(annotation) == expected
