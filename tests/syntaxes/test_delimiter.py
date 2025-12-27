"""Tests for delimiter syntax implementations."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from pydantic import ValidationError

from hother.streamblocks.core.models import Block, BlockCandidate
from hother.streamblocks.core.types import BaseContent, BaseMetadata, SectionType
from hother.streamblocks.syntaxes.delimiter import (
    DelimiterFrontmatterSyntax,
    DelimiterPreambleSyntax,
)


class TestDelimiterPreambleSyntaxDetectLine:
    """Tests for DelimiterPreambleSyntax.detect_line()."""

    def test_detect_opening_line(self) -> None:
        """Test detecting an opening line."""
        syntax = DelimiterPreambleSyntax()

        result = syntax.detect_line("!!myblock:file")

        assert result.is_opening is True
        assert result.metadata is not None
        assert result.metadata["id"] == "myblock"
        assert result.metadata["block_type"] == "file"

    def test_detect_opening_with_params(self) -> None:
        """Test detecting opening line with extra parameters."""
        syntax = DelimiterPreambleSyntax()

        result = syntax.detect_line("!!block1:type:param1:param2")

        assert result.is_opening is True
        assert result.metadata is not None
        assert result.metadata["param_0"] == "param1"
        assert result.metadata["param_1"] == "param2"

    def test_detect_closing_line(self) -> None:
        """Test detecting a closing line."""
        syntax = DelimiterPreambleSyntax()
        candidate = MagicMock(spec=BlockCandidate)

        result = syntax.detect_line("!!end", candidate)

        assert result.is_closing is True

    def test_detect_non_matching_line(self) -> None:
        """Test detecting a non-matching line."""
        syntax = DelimiterPreambleSyntax()

        result = syntax.detect_line("regular text")

        assert result.is_opening is False
        assert result.is_closing is False

    def test_detect_content_line_with_candidate(self) -> None:
        """Test content line when inside block (branch 68->71)."""
        syntax = DelimiterPreambleSyntax()
        candidate = MagicMock(spec=BlockCandidate)

        # Line that is NOT the closing marker
        result = syntax.detect_line("some content line", candidate)

        # Should return default DetectionResult
        assert result.is_opening is False
        assert result.is_closing is False
        assert result.is_metadata_boundary is False

    def test_detect_with_custom_delimiter(self) -> None:
        """Test detection with custom delimiter."""
        syntax = DelimiterPreambleSyntax(delimiter="@@")

        result = syntax.detect_line("@@myblock:file")

        assert result.is_opening is True
        assert result.metadata["id"] == "myblock"


class TestDelimiterPreambleSyntaxShouldAccumulateMetadata:
    """Tests for DelimiterPreambleSyntax.should_accumulate_metadata()."""

    def test_should_accumulate_metadata_returns_false(self) -> None:
        """Test that preamble syntax never accumulates metadata (line 75)."""
        syntax = DelimiterPreambleSyntax()
        candidate = MagicMock(spec=BlockCandidate)

        result = syntax.should_accumulate_metadata(candidate)

        assert result is False


class TestDelimiterPreambleSyntaxExtractBlockType:
    """Tests for DelimiterPreambleSyntax.extract_block_type()."""

    def test_extract_block_type_with_empty_lines(self) -> None:
        """Test extract_block_type with empty candidate lines (lines 79-80)."""
        syntax = DelimiterPreambleSyntax()
        candidate = MagicMock(spec=BlockCandidate)
        candidate.lines = []

        result = syntax.extract_block_type(candidate)

        assert result is None

    def test_extract_block_type_success(self) -> None:
        """Test extracting block_type from opening line."""
        syntax = DelimiterPreambleSyntax()
        candidate = MagicMock(spec=BlockCandidate)
        candidate.lines = ["!!myblock:file", "content", "!!end"]

        result = syntax.extract_block_type(candidate)

        assert result == "file"

    def test_extract_block_type_no_metadata(self) -> None:
        """Test extract_block_type when detection returns no metadata (line 87)."""
        syntax = DelimiterPreambleSyntax()
        candidate = MagicMock(spec=BlockCandidate)
        candidate.lines = ["not a valid opening line"]

        result = syntax.extract_block_type(candidate)

        assert result is None


class TestDelimiterPreambleSyntaxParseBlock:
    """Tests for DelimiterPreambleSyntax.parse_block()."""

    def test_parse_block_missing_metadata(self) -> None:
        """Test parse_block with malformed opening (no metadata) (line 107)."""
        syntax = DelimiterPreambleSyntax()
        candidate = MagicMock(spec=BlockCandidate)
        candidate.lines = ["not a valid opening", "content", "!!end"]

        result = syntax.parse_block(candidate)

        assert result.success is False
        assert "Missing metadata" in result.error

    def test_parse_block_success(self) -> None:
        """Test successful block parsing."""
        syntax = DelimiterPreambleSyntax()
        candidate = MagicMock(spec=BlockCandidate)
        candidate.lines = ["!!myblock:file", "content here", "!!end"]

        result = syntax.parse_block(candidate)

        assert result.success is True
        assert result.metadata is not None
        assert result.metadata.id == "myblock"
        assert result.metadata.block_type == "file"

    def test_parse_block_with_custom_metadata_validation_error(self) -> None:
        """Test parse_block with custom metadata that fails validation (lines 119-120)."""
        syntax = DelimiterPreambleSyntax()
        candidate = MagicMock(spec=BlockCandidate)
        candidate.lines = ["!!myblock:file", "content", "!!end"]

        class StrictMetadata(BaseMetadata):
            required_field: str  # This is required but won't be provided

        class StrictBlock(Block[StrictMetadata, BaseContent]):
            pass

        result = syntax.parse_block(candidate, StrictBlock)

        assert result.success is False
        assert "validation error" in result.error.lower()
        assert result.exception is not None

    def test_parse_block_with_content_validation_error(self) -> None:
        """Test parse_block with content that fails validation (lines 130-131)."""
        syntax = DelimiterPreambleSyntax()
        candidate = MagicMock(spec=BlockCandidate)
        candidate.lines = ["!!myblock:file", "content", "!!end"]

        class FailingContent(BaseContent):
            @classmethod
            def parse(cls, raw_text: str) -> FailingContent:
                raise ValidationError.from_exception_data("test", [])

        class FailingBlock(Block[BaseMetadata, FailingContent]):
            pass

        result = syntax.parse_block(candidate, FailingBlock)

        assert result.success is False
        assert "content validation error" in result.error.lower()

    def test_parse_block_with_content_value_error(self) -> None:
        """Test parse_block when content parse raises ValueError (lines 132-133)."""
        syntax = DelimiterPreambleSyntax()
        candidate = MagicMock(spec=BlockCandidate)
        candidate.lines = ["!!myblock:file", "bad content", "!!end"]

        class FailingContent(BaseContent):
            @classmethod
            def parse(cls, raw_text: str) -> FailingContent:
                msg = "Content parsing failed"
                raise ValueError(msg)

        class FailingBlock(Block[BaseMetadata, FailingContent]):
            pass

        result = syntax.parse_block(candidate, FailingBlock)

        assert result.success is False
        assert "Invalid content" in result.error

    def test_parse_block_metadata_type_error(self) -> None:
        """Test parse_block when metadata class raises TypeError (lines 116-117)."""
        from unittest.mock import patch

        syntax = DelimiterPreambleSyntax()
        candidate = MagicMock(spec=BlockCandidate)
        candidate.lines = ["!!myblock:file", "content", "!!end"]

        class BadMetadata:
            def __init__(self, **kwargs: Any) -> None:
                msg = "Cannot create metadata"
                raise TypeError(msg)

        with patch(
            "hother.streamblocks.syntaxes.delimiter.extract_block_types",
            return_value=(BadMetadata, BaseContent),
        ):

            class FakeBlock:
                pass

            result = syntax.parse_block(candidate, FakeBlock)

        assert result.success is False
        assert "Invalid metadata" in result.error


class TestDelimiterPreambleSyntaxParseMetadataEarly:
    """Tests for DelimiterPreambleSyntax.parse_metadata_early()."""

    def test_parse_metadata_early_empty_lines(self) -> None:
        """Test parse_metadata_early with empty candidate lines (lines 147-148)."""
        syntax = DelimiterPreambleSyntax()
        candidate = MagicMock(spec=BlockCandidate)
        candidate.lines = []

        result = syntax.parse_metadata_early(candidate)

        assert result is None

    def test_parse_metadata_early_no_match(self) -> None:
        """Test parse_metadata_early when line doesn't match pattern (line 154)."""
        syntax = DelimiterPreambleSyntax()
        candidate = MagicMock(spec=BlockCandidate)
        candidate.lines = ["not a valid opening line"]

        result = syntax.parse_metadata_early(candidate)

        assert result is None

    def test_parse_metadata_early_success(self) -> None:
        """Test successful early metadata parsing."""
        syntax = DelimiterPreambleSyntax()
        candidate = MagicMock(spec=BlockCandidate)
        candidate.lines = ["!!myblock:file:extra"]

        result = syntax.parse_metadata_early(candidate)

        assert result is not None
        assert result["id"] == "myblock"
        assert result["block_type"] == "file"


class TestDelimiterPreambleSyntaxParseContentEarly:
    """Tests for DelimiterPreambleSyntax.parse_content_early()."""

    def test_parse_content_early_insufficient_lines(self) -> None:
        """Test parse_content_early with less than 2 lines (lines 161-162)."""
        syntax = DelimiterPreambleSyntax()
        candidate = MagicMock(spec=BlockCandidate)
        candidate.lines = ["!!myblock:file"]  # Only 1 line

        result = syntax.parse_content_early(candidate)

        assert result is None

    def test_parse_content_early_two_lines(self) -> None:
        """Test parse_content_early with exactly 2 lines."""
        syntax = DelimiterPreambleSyntax()
        candidate = MagicMock(spec=BlockCandidate)
        candidate.lines = ["!!myblock:file", "content"]

        result = syntax.parse_content_early(candidate)

        assert result is not None
        assert result["raw_content"] == "content"

    def test_parse_content_early_multiple_lines(self) -> None:
        """Test parse_content_early with multiple content lines."""
        syntax = DelimiterPreambleSyntax()
        candidate = MagicMock(spec=BlockCandidate)
        candidate.lines = ["!!myblock:file", "line1", "line2", "!!end"]

        result = syntax.parse_content_early(candidate)

        assert result is not None
        assert result["raw_content"] == "line1\nline2"


class TestDelimiterFrontmatterSyntaxDetectLine:
    """Tests for DelimiterFrontmatterSyntax.detect_line()."""

    def test_detect_opening(self) -> None:
        """Test detecting opening delimiter."""
        syntax = DelimiterFrontmatterSyntax()

        result = syntax.detect_line("!!start")

        assert result.is_opening is True

    def test_detect_non_opening_without_candidate(self) -> None:
        """Test non-opening line without candidate (branch 196->220)."""
        syntax = DelimiterFrontmatterSyntax()

        # Line that is NOT the start delimiter
        result = syntax.detect_line("some regular text")

        # Should return default DetectionResult
        assert result.is_opening is False
        assert result.is_closing is False
        assert result.is_metadata_boundary is False

    def test_detect_frontmatter_start_in_header(self) -> None:
        """Test detecting frontmatter start in header section."""
        syntax = DelimiterFrontmatterSyntax()
        candidate = MagicMock(spec=BlockCandidate)
        candidate.current_section = SectionType.HEADER

        result = syntax.detect_line("---", candidate)

        assert result.is_metadata_boundary is True
        candidate.transition_to_metadata.assert_called_once()

    def test_detect_empty_line_in_header(self) -> None:
        """Test skipping empty lines in header section."""
        syntax = DelimiterFrontmatterSyntax()
        candidate = MagicMock(spec=BlockCandidate)
        candidate.current_section = SectionType.HEADER

        result = syntax.detect_line("", candidate)

        assert result.is_opening is False
        assert result.is_closing is False

    def test_detect_content_line_in_header_no_frontmatter(self) -> None:
        """Test moving to content when no frontmatter in header (lines 213-214)."""
        syntax = DelimiterFrontmatterSyntax()
        candidate = MagicMock(spec=BlockCandidate)
        candidate.current_section = SectionType.HEADER
        candidate.content_lines = []

        syntax.detect_line("content line", candidate)

        candidate.transition_to_content.assert_called_once()
        assert "content line" in candidate.content_lines

    def test_detect_frontmatter_end_in_metadata(self) -> None:
        """Test detecting frontmatter end in metadata section."""
        syntax = DelimiterFrontmatterSyntax()
        candidate = MagicMock(spec=BlockCandidate)
        candidate.current_section = SectionType.METADATA

        result = syntax.detect_line("---", candidate)

        assert result.is_metadata_boundary is True
        candidate.transition_to_content.assert_called_once()

    def test_detect_metadata_line(self) -> None:
        """Test accumulating metadata lines."""
        syntax = DelimiterFrontmatterSyntax()
        candidate = MagicMock(spec=BlockCandidate)
        candidate.current_section = SectionType.METADATA
        candidate.metadata_lines = []

        syntax.detect_line("key: value", candidate)

        assert "key: value" in candidate.metadata_lines

    def test_detect_closing_in_content(self) -> None:
        """Test detecting closing delimiter in content section."""
        syntax = DelimiterFrontmatterSyntax()
        candidate = MagicMock(spec=BlockCandidate)
        candidate.current_section = SectionType.CONTENT

        result = syntax.detect_line("!!end", candidate)

        assert result.is_closing is True

    def test_detect_content_line(self) -> None:
        """Test accumulating content lines and return value (branch 220->225)."""
        syntax = DelimiterFrontmatterSyntax()
        candidate = MagicMock(spec=BlockCandidate)
        candidate.current_section = SectionType.CONTENT
        candidate.content_lines = []

        result = syntax.detect_line("some content", candidate)

        assert "some content" in candidate.content_lines
        # Verify return value is default DetectionResult
        assert result.is_opening is False
        assert result.is_closing is False
        assert result.is_metadata_boundary is False

    def test_detect_line_unknown_section_returns_default(self) -> None:
        """Test detect_line with unknown section returns DetectionResult (branch 215->220)."""
        from hother.streamblocks.core.models import BlockCandidate

        syntax = DelimiterFrontmatterSyntax()
        candidate = BlockCandidate(syntax=syntax, start_line=1)
        # Set to an unexpected section value (bypassing type safety for testing)
        candidate.current_section = "unknown"  # type: ignore[assignment]

        result = syntax.detect_line("some line", candidate)

        # Should return default DetectionResult without modifying candidate
        assert result.is_opening is False
        assert result.is_closing is False
        assert result.is_metadata_boundary is False


class TestDelimiterFrontmatterSyntaxShouldAccumulateMetadata:
    """Tests for DelimiterFrontmatterSyntax.should_accumulate_metadata()."""

    def test_should_accumulate_in_header(self) -> None:
        """Test should_accumulate_metadata returns True in header section."""
        syntax = DelimiterFrontmatterSyntax()
        candidate = MagicMock(spec=BlockCandidate)
        candidate.current_section = SectionType.HEADER

        result = syntax.should_accumulate_metadata(candidate)

        assert result is True

    def test_should_accumulate_in_metadata(self) -> None:
        """Test should_accumulate_metadata returns True in metadata section."""
        syntax = DelimiterFrontmatterSyntax()
        candidate = MagicMock(spec=BlockCandidate)
        candidate.current_section = SectionType.METADATA

        result = syntax.should_accumulate_metadata(candidate)

        assert result is True

    def test_should_not_accumulate_in_content(self) -> None:
        """Test should_accumulate_metadata returns False in content section (line 229)."""
        syntax = DelimiterFrontmatterSyntax()
        candidate = MagicMock(spec=BlockCandidate)
        candidate.current_section = SectionType.CONTENT

        result = syntax.should_accumulate_metadata(candidate)

        assert result is False


class TestDelimiterFrontmatterSyntaxExtractBlockType:
    """Tests for DelimiterFrontmatterSyntax.extract_block_type()."""

    def test_extract_block_type_from_frontmatter(self) -> None:
        """Test extracting block_type from YAML frontmatter."""
        syntax = DelimiterFrontmatterSyntax()
        candidate = MagicMock(spec=BlockCandidate)
        candidate.metadata_lines = ["block_type: file", "id: test"]

        result = syntax.extract_block_type(candidate)

        assert result == "file"

    def test_extract_block_type_no_frontmatter(self) -> None:
        """Test extract_block_type with no frontmatter."""
        syntax = DelimiterFrontmatterSyntax()
        candidate = MagicMock(spec=BlockCandidate)
        candidate.metadata_lines = []

        result = syntax.extract_block_type(candidate)

        assert result is None

    def test_extract_block_type_no_block_type_key(self) -> None:
        """Test extract_block_type when block_type not in metadata."""
        syntax = DelimiterFrontmatterSyntax()
        candidate = MagicMock(spec=BlockCandidate)
        candidate.metadata_lines = ["id: test", "other: value"]

        result = syntax.extract_block_type(candidate)

        assert result is None


class TestDelimiterFrontmatterSyntaxParseBlock:
    """Tests for DelimiterFrontmatterSyntax.parse_block()."""

    def test_parse_block_yaml_error(self) -> None:
        """Test parse_block with invalid YAML (line 255)."""
        syntax = DelimiterFrontmatterSyntax()
        candidate = MagicMock(spec=BlockCandidate)
        candidate.metadata_lines = ["invalid: [yaml"]  # Unclosed bracket
        candidate.content_lines = ["content"]
        candidate.compute_hash = MagicMock(return_value="abc123")

        result = syntax.parse_block(candidate)

        assert result.success is False
        assert "YAML parse error" in result.error

    def test_parse_block_fails_without_required_fields(self) -> None:
        """Test that parse fails when required id and block_type are missing."""
        syntax = DelimiterFrontmatterSyntax()
        candidate = MagicMock(spec=BlockCandidate)
        candidate.metadata_lines = []  # No frontmatter - missing required fields
        candidate.content_lines = ["content"]

        result = syntax.parse_block(candidate)

        assert result.success is False
        assert "validation error" in result.error.lower()
        assert "id" in result.error.lower() or "block_type" in result.error.lower()

    def test_parse_block_metadata_validation_error(self) -> None:
        """Test parse_block with metadata validation error (lines 269-270)."""
        syntax = DelimiterFrontmatterSyntax()
        candidate = MagicMock(spec=BlockCandidate)
        candidate.metadata_lines = ["id: test", "block_type: file"]
        candidate.content_lines = ["content"]

        class StrictMetadata(BaseMetadata):
            required_field: str  # Required but not provided

        class StrictBlock(Block[StrictMetadata, BaseContent]):
            pass

        result = syntax.parse_block(candidate, StrictBlock)

        assert result.success is False
        assert "validation error" in result.error.lower()

    def test_parse_block_metadata_type_error(self) -> None:
        """Test parse_block with metadata type error (lines 271-272)."""
        syntax = DelimiterFrontmatterSyntax()
        candidate = MagicMock(spec=BlockCandidate)
        candidate.metadata_lines = ["id: test", "block_type: file"]
        candidate.content_lines = ["content"]

        class BadMetadata:
            def __init__(self, **kwargs: Any) -> None:
                msg = "Cannot create metadata"
                raise TypeError(msg)

        # Mock extract_block_types to return our bad class
        from unittest.mock import patch

        with patch(
            "hother.streamblocks.syntaxes.delimiter.extract_block_types",
            return_value=(BadMetadata, BaseContent),
        ):

            class FakeBlock:
                pass

            result = syntax.parse_block(candidate, FakeBlock)

        assert result.success is False
        assert "Invalid metadata" in result.error

    def test_parse_block_content_validation_error(self) -> None:
        """Test parse_block with content validation error (lines 279-280)."""
        syntax = DelimiterFrontmatterSyntax()
        candidate = MagicMock(spec=BlockCandidate)
        candidate.metadata_lines = ["id: test", "block_type: file"]
        candidate.content_lines = ["content"]

        class FailingContent(BaseContent):
            @classmethod
            def parse(cls, raw_text: str) -> FailingContent:
                raise ValidationError.from_exception_data("test", [])

        class FailingBlock(Block[BaseMetadata, FailingContent]):
            pass

        result = syntax.parse_block(candidate, FailingBlock)

        assert result.success is False
        assert "content validation error" in result.error.lower()

    def test_parse_block_content_value_error(self) -> None:
        """Test parse_block with content ValueError (lines 281-282)."""
        syntax = DelimiterFrontmatterSyntax()
        candidate = MagicMock(spec=BlockCandidate)
        candidate.metadata_lines = ["id: test", "block_type: file"]
        candidate.content_lines = ["content"]

        class FailingContent(BaseContent):
            @classmethod
            def parse(cls, raw_text: str) -> FailingContent:
                msg = "Parse failed"
                raise ValueError(msg)

        class FailingBlock(Block[BaseMetadata, FailingContent]):
            pass

        result = syntax.parse_block(candidate, FailingBlock)

        assert result.success is False
        assert "Invalid content" in result.error


class TestDelimiterFrontmatterSyntaxParseMetadataEarly:
    """Tests for DelimiterFrontmatterSyntax.parse_metadata_early()."""

    def test_parse_metadata_early_empty(self) -> None:
        """Test parse_metadata_early with empty metadata lines."""
        syntax = DelimiterFrontmatterSyntax()
        candidate = MagicMock(spec=BlockCandidate)
        candidate.metadata_lines = []

        result = syntax.parse_metadata_early(candidate)

        assert result is None

    def test_parse_metadata_early_success(self) -> None:
        """Test successful early metadata parsing."""
        syntax = DelimiterFrontmatterSyntax()
        candidate = MagicMock(spec=BlockCandidate)
        candidate.metadata_lines = ["id: test", "block_type: file"]

        result = syntax.parse_metadata_early(candidate)

        assert result is not None
        assert result["id"] == "test"


class TestDelimiterFrontmatterSyntaxParseContentEarly:
    """Tests for DelimiterFrontmatterSyntax.parse_content_early()."""

    def test_parse_content_early_empty(self) -> None:
        """Test parse_content_early with empty content."""
        syntax = DelimiterFrontmatterSyntax()
        candidate = MagicMock(spec=BlockCandidate)
        candidate.content_lines = []

        result = syntax.parse_content_early(candidate)

        assert result is not None
        assert result["raw_content"] == ""

    def test_parse_content_early_with_content(self) -> None:
        """Test parse_content_early with content lines."""
        syntax = DelimiterFrontmatterSyntax()
        candidate = MagicMock(spec=BlockCandidate)
        candidate.content_lines = ["line1", "line2"]

        result = syntax.parse_content_early(candidate)

        assert result is not None
        assert result["raw_content"] == "line1\nline2"


class TestDelimiterSyntaxValidateBlock:
    """Tests for validate_block methods."""

    def test_preamble_validate_block_returns_true(self) -> None:
        """Test DelimiterPreambleSyntax.validate_block returns True."""
        syntax = DelimiterPreambleSyntax()
        block = MagicMock()

        result = syntax.validate_block(block)

        assert result is True

    def test_frontmatter_validate_block_returns_true(self) -> None:
        """Test DelimiterFrontmatterSyntax.validate_block returns True."""
        syntax = DelimiterFrontmatterSyntax()
        block = MagicMock()

        result = syntax.validate_block(block)

        assert result is True


class TestContentParserProtocol:
    """Tests for ContentParser protocol."""

    def test_content_parser_protocol_is_runtime_checkable(self) -> None:
        """ContentParser protocol supports isinstance checks."""
        from hother.streamblocks.syntaxes.delimiter import ContentParser

        class MyContent(BaseContent):
            @classmethod
            def parse(cls, raw_text: str) -> MyContent:
                return cls(raw_content=raw_text)

        # The class itself should satisfy the protocol (has parse classmethod)
        assert isinstance(MyContent, ContentParser)

    def test_base_content_satisfies_content_parser(self) -> None:
        """BaseContent satisfies ContentParser protocol."""
        from hother.streamblocks.syntaxes.delimiter import ContentParser

        # BaseContent has a parse classmethod
        assert isinstance(BaseContent, ContentParser)
