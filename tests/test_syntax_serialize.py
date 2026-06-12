"""Tests for syntax serialize_block / describe_format methods."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

import pytest

from hother.streamblocks.core.models import Block
from hother.streamblocks.core.types import BaseContent, BaseMetadata, DetectionResult, ParseResult
from hother.streamblocks.syntaxes.base import BaseSyntax
from hother.streamblocks.syntaxes.delimiter import DelimiterFrontmatterSyntax, DelimiterPreambleSyntax
from hother.streamblocks.syntaxes.markdown import MarkdownFrontmatterSyntax

if TYPE_CHECKING:
    from hother.streamblocks.core.models import BlockCandidate


class _Meta(BaseMetadata):
    block_type: Literal["note"] = "note"


class _ParamMeta(BaseMetadata):
    block_type: Literal["op"] = "op"
    param_0: str = ""
    param_1: str = ""


class Note(Block[_Meta, BaseContent]):
    """A note block."""


class Op(Block[_ParamMeta, BaseContent]):
    """An operation block with positional params."""


def _note() -> Note:
    return Note(metadata=_Meta(id="n1"), content=BaseContent(raw_content="hello"))


def test_delimiter_preamble_serialize_roundtrips_through_parser() -> None:
    syntax = DelimiterPreambleSyntax()
    text = syntax.serialize_block(_note())
    assert text == "!!n1:note\nhello\n!!end"


def test_delimiter_preamble_serialize_emits_params() -> None:
    syntax = DelimiterPreambleSyntax()
    block = Op(metadata=_ParamMeta(id="o1", param_0="create", param_1="urgent"), content=BaseContent(raw_content="x"))
    assert syntax.serialize_block(block) == "!!o1:op:create:urgent\nx\n!!end"


def test_delimiter_frontmatter_serialize() -> None:
    syntax = DelimiterFrontmatterSyntax()
    text = syntax.serialize_block(_note())
    assert text.startswith("!!start\n---\n")
    assert "id: n1" in text
    assert "block_type: note" in text
    assert text.endswith("hello\n!!end")


def test_markdown_serialize_with_info_string() -> None:
    syntax = MarkdownFrontmatterSyntax(info_string="note")
    text = syntax.serialize_block(_note())
    assert text.startswith("```note\n---\n")
    assert text.endswith("hello\n```")


def test_markdown_serialize_without_info_string() -> None:
    syntax = MarkdownFrontmatterSyntax()
    text = syntax.serialize_block(_note())
    assert text.startswith("```\n---\n")


@pytest.mark.parametrize(
    ("syntax", "needle"),
    [
        (DelimiterPreambleSyntax(), "Delimiter Preamble Syntax"),
        (DelimiterFrontmatterSyntax(), "Delimiter Frontmatter Syntax"),
        (MarkdownFrontmatterSyntax(info_string="note"), "Markdown Frontmatter Syntax"),
        (MarkdownFrontmatterSyntax(), "[info_string]"),
    ],
)
def test_describe_format_contains_expected_header(syntax: BaseSyntax, needle: str) -> None:
    assert needle in syntax.describe_format()


class _BareSyntax(BaseSyntax):
    """Syntax that does not override serialize_block/describe_format."""

    def detect_line(self, line: str, candidate: BlockCandidate | None) -> DetectionResult:
        return DetectionResult()

    def should_accumulate_metadata(self, candidate: BlockCandidate) -> bool:
        return False

    def extract_block_type(self, candidate: BlockCandidate) -> str | None:
        return None

    def parse_block(
        self, candidate: BlockCandidate, block_class: type[Any] | None = None
    ) -> ParseResult[BaseMetadata, BaseContent]:
        return ParseResult(success=False, error="not implemented")


def test_base_serialize_block_raises() -> None:
    with pytest.raises(NotImplementedError, match="serialize_block"):
        _BareSyntax().serialize_block(_note())


def test_base_describe_format_default() -> None:
    assert _BareSyntax().describe_format() == "_BareSyntax: no format description available."
