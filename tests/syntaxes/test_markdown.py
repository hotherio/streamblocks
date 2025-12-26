"""Tests for markdown syntax module."""

from __future__ import annotations

from unittest.mock import MagicMock

from pydantic import ValidationError

from hother.streamblocks.core.models import Block, BlockCandidate
from hother.streamblocks.core.types import BaseContent, BaseMetadata, SectionType
from hother.streamblocks.syntaxes.markdown import MarkdownFrontmatterSyntax


class TestMarkdownFrontmatterSyntaxInit:
    """Tests for MarkdownFrontmatterSyntax initialization."""

    def test_default_initialization(self) -> None:
        """Test default initialization values."""
        syntax = MarkdownFrontmatterSyntax()

        assert syntax.fence == "```"
        assert syntax.info_string is None

    def test_custom_fence(self) -> None:
        """Test initialization with custom fence."""
        syntax = MarkdownFrontmatterSyntax(fence="~~~")

        assert syntax.fence == "~~~"

    def test_custom_info_string(self) -> None:
        """Test initialization with info_string."""
        syntax = MarkdownFrontmatterSyntax(info_string="python")

        assert syntax.info_string == "python"


class TestMarkdownFrontmatterSyntaxDetectLine:
    """Tests for MarkdownFrontmatterSyntax.detect_line()."""

    def test_detect_opening_fence(self) -> None:
        """Test detecting opening fence without candidate."""
        syntax = MarkdownFrontmatterSyntax()

        result = syntax.detect_line("```")

        assert result.is_opening is True

    def test_detect_opening_fence_with_info_string(self) -> None:
        """Test detecting opening fence with info string."""
        syntax = MarkdownFrontmatterSyntax(info_string="python")

        result = syntax.detect_line("```python")

        assert result.is_opening is True

    def test_no_opening_without_match(self) -> None:
        """Test that non-matching line doesn't trigger opening."""
        syntax = MarkdownFrontmatterSyntax()

        result = syntax.detect_line("regular text")

        assert result.is_opening is False

    def test_detect_frontmatter_start_in_header(self) -> None:
        """Test detecting frontmatter start (---) in header section."""
        syntax = MarkdownFrontmatterSyntax()
        candidate = BlockCandidate(syntax=syntax, start_line=1)
        candidate.current_section = SectionType.HEADER

        result = syntax.detect_line("---", candidate)

        assert result.is_metadata_boundary is True
        assert candidate.current_section == SectionType.METADATA

    def test_empty_line_in_header_stays_in_header(self) -> None:
        """Test that empty lines in header section don't change state."""
        syntax = MarkdownFrontmatterSyntax()
        candidate = BlockCandidate(syntax=syntax, start_line=1)
        candidate.current_section = SectionType.HEADER

        result = syntax.detect_line("", candidate)

        assert result.is_opening is False
        assert result.is_metadata_boundary is False
        assert candidate.current_section == SectionType.HEADER

    def test_content_line_in_header_moves_to_content(self) -> None:
        """Test that non-empty, non-frontmatter line in header moves to content.

        This covers lines 69-70: Content without frontmatter.
        """
        syntax = MarkdownFrontmatterSyntax()
        candidate = BlockCandidate(syntax=syntax, start_line=1)
        candidate.current_section = SectionType.HEADER

        result = syntax.detect_line("Some content directly after fence", candidate)

        assert candidate.current_section == SectionType.CONTENT
        assert "Some content directly after fence" in candidate.content_lines
        assert result.is_opening is False
        assert result.is_metadata_boundary is False

    def test_content_line_in_header_no_frontmatter_fence(self) -> None:
        """Test handling content immediately after fence (no --- frontmatter)."""
        syntax = MarkdownFrontmatterSyntax()
        candidate = BlockCandidate(syntax=syntax, start_line=1)
        candidate.current_section = SectionType.HEADER

        # First content line after fence
        syntax.detect_line("print('hello')", candidate)

        assert candidate.current_section == SectionType.CONTENT
        assert candidate.content_lines == ["print('hello')"]

    def test_frontmatter_end_in_metadata_section(self) -> None:
        """Test detecting frontmatter end (---) in metadata section."""
        syntax = MarkdownFrontmatterSyntax()
        candidate = BlockCandidate(syntax=syntax, start_line=1)
        candidate.current_section = SectionType.METADATA

        result = syntax.detect_line("---", candidate)

        assert result.is_metadata_boundary is True
        assert candidate.current_section == SectionType.CONTENT

    def test_metadata_line_accumulates(self) -> None:
        """Test that metadata lines are accumulated."""
        syntax = MarkdownFrontmatterSyntax()
        candidate = BlockCandidate(syntax=syntax, start_line=1)
        candidate.current_section = SectionType.METADATA

        syntax.detect_line("key: value", candidate)

        assert "key: value" in candidate.metadata_lines

    def test_closing_fence_in_content_section(self) -> None:
        """Test detecting closing fence in content section."""
        syntax = MarkdownFrontmatterSyntax()
        candidate = BlockCandidate(syntax=syntax, start_line=1)
        candidate.current_section = SectionType.CONTENT

        result = syntax.detect_line("```", candidate)

        assert result.is_closing is True

    def test_content_line_accumulates(self) -> None:
        """Test that content lines are accumulated and return value (branch 77->83)."""
        syntax = MarkdownFrontmatterSyntax()
        candidate = BlockCandidate(syntax=syntax, start_line=1)
        candidate.current_section = SectionType.CONTENT

        result = syntax.detect_line("content line", candidate)

        assert "content line" in candidate.content_lines
        # Verify return value is default DetectionResult
        assert result.is_opening is False
        assert result.is_closing is False
        assert result.is_metadata_boundary is False

    def test_detect_line_unknown_section_returns_default(self) -> None:
        """Test detect_line with unknown section returns DetectionResult (branch 77->83)."""
        syntax = MarkdownFrontmatterSyntax()
        candidate = BlockCandidate(syntax=syntax, start_line=1)
        # Set to an unexpected section value
        candidate.current_section = "unknown"

        result = syntax.detect_line("some line", candidate)

        # Should return default DetectionResult without modifying candidate
        assert result.is_opening is False
        assert result.is_closing is False
        assert result.is_metadata_boundary is False


class TestMarkdownFrontmatterSyntaxShouldAccumulateMetadata:
    """Tests for MarkdownFrontmatterSyntax.should_accumulate_metadata()."""

    def test_should_accumulate_in_header_section(self) -> None:
        """Test returns True when in header section."""
        syntax = MarkdownFrontmatterSyntax()
        candidate = BlockCandidate(syntax=syntax, start_line=1)
        candidate.current_section = SectionType.HEADER

        result = syntax.should_accumulate_metadata(candidate)

        assert result is True

    def test_should_accumulate_in_metadata_section(self) -> None:
        """Test returns True when in metadata section."""
        syntax = MarkdownFrontmatterSyntax()
        candidate = BlockCandidate(syntax=syntax, start_line=1)
        candidate.current_section = SectionType.METADATA

        result = syntax.should_accumulate_metadata(candidate)

        assert result is True

    def test_should_not_accumulate_in_content_section(self) -> None:
        """Test returns False when in content section.

        This covers line 87.
        """
        syntax = MarkdownFrontmatterSyntax()
        candidate = BlockCandidate(syntax=syntax, start_line=1)
        candidate.current_section = SectionType.CONTENT

        result = syntax.should_accumulate_metadata(candidate)

        assert result is False


class TestMarkdownFrontmatterSyntaxExtractBlockType:
    """Tests for MarkdownFrontmatterSyntax.extract_block_type()."""

    def test_extract_from_yaml_metadata(self) -> None:
        """Test extracting block_type from YAML metadata."""
        syntax = MarkdownFrontmatterSyntax()
        candidate = BlockCandidate(syntax=syntax, start_line=1)
        candidate.metadata_lines = ["block_type: custom"]

        result = syntax.extract_block_type(candidate)

        assert result == "custom"

    def test_extract_fallback_to_info_string_when_no_metadata(self) -> None:
        """Test fallback to info_string when no metadata lines.

        This covers line 93.
        """
        syntax = MarkdownFrontmatterSyntax(info_string="python")
        candidate = BlockCandidate(syntax=syntax, start_line=1)
        candidate.metadata_lines = []

        result = syntax.extract_block_type(candidate)

        assert result == "python"

    def test_extract_fallback_to_info_string_when_no_block_type_in_metadata(self) -> None:
        """Test fallback to info_string when block_type not in metadata.

        This covers line 98 (partially) and line 100.
        """
        syntax = MarkdownFrontmatterSyntax(info_string="javascript")
        candidate = BlockCandidate(syntax=syntax, start_line=1)
        candidate.metadata_lines = ["author: test"]  # No block_type

        result = syntax.extract_block_type(candidate)

        assert result == "javascript"

    def test_extract_returns_none_when_no_info_string_and_no_metadata(self) -> None:
        """Test returns None when no info_string and no metadata."""
        syntax = MarkdownFrontmatterSyntax()
        candidate = BlockCandidate(syntax=syntax, start_line=1)
        candidate.metadata_lines = []

        result = syntax.extract_block_type(candidate)

        assert result is None

    def test_extract_with_invalid_yaml_returns_info_string(self) -> None:
        """Test that invalid YAML returns info_string fallback."""
        syntax = MarkdownFrontmatterSyntax(info_string="default")
        candidate = BlockCandidate(syntax=syntax, start_line=1)
        candidate.metadata_lines = ["[invalid: yaml"]  # Invalid YAML

        result = syntax.extract_block_type(candidate)

        assert result == "default"


class TestMarkdownFrontmatterSyntaxParseBlock:
    """Tests for MarkdownFrontmatterSyntax.parse_block()."""

    def test_parse_block_with_base_classes(self) -> None:
        """Test parsing with default base classes."""
        syntax = MarkdownFrontmatterSyntax()
        candidate = BlockCandidate(syntax=syntax, start_line=1)
        candidate.metadata_lines = ["block_type: test", "id: test-1"]
        candidate.content_lines = ["Some content"]

        result = syntax.parse_block(candidate)

        assert result.success is True
        assert result.metadata is not None
        assert result.metadata.id == "test-1"
        assert result.metadata.block_type == "test"

    def test_parse_block_fails_when_id_missing(self) -> None:
        """Test that parse fails when id is missing in BaseMetadata."""
        syntax = MarkdownFrontmatterSyntax()
        candidate = BlockCandidate(syntax=syntax, start_line=1)
        candidate.metadata_lines = ["block_type: test"]  # Missing id
        candidate.content_lines = ["content"]

        result = syntax.parse_block(candidate)

        assert result.success is False
        assert "validation error" in result.error.lower()
        assert "id" in result.error.lower()

    def test_parse_block_fails_when_block_type_missing(self) -> None:
        """Test that parse fails when block_type is missing."""
        syntax = MarkdownFrontmatterSyntax(info_string="python")
        candidate = BlockCandidate(syntax=syntax, start_line=1)
        candidate.metadata_lines = ["id: test-1"]  # No block_type
        candidate.content_lines = ["print('hello')"]

        result = syntax.parse_block(candidate)

        # info_string does not auto-fill block_type for BaseMetadata
        assert result.success is False
        assert "validation error" in result.error.lower()
        assert "block_type" in result.error.lower()

    def test_parse_block_fails_when_both_fields_missing(self) -> None:
        """Test parse fails when both id and block_type are missing."""
        syntax = MarkdownFrontmatterSyntax()  # No info_string
        candidate = BlockCandidate(syntax=syntax, start_line=1)
        candidate.metadata_lines = ["author: test"]  # No id or block_type
        candidate.content_lines = ["content"]

        result = syntax.parse_block(candidate)

        assert result.success is False
        assert "validation error" in result.error.lower()

    def test_parse_block_with_yaml_error(self) -> None:
        """Test parse returns error on invalid YAML.

        This covers line 119.
        """
        syntax = MarkdownFrontmatterSyntax()
        candidate = BlockCandidate(syntax=syntax, start_line=1)
        candidate.metadata_lines = ["[unclosed: bracket"]  # Invalid YAML
        candidate.content_lines = ["content"]

        result = syntax.parse_block(candidate)

        assert result.success is False
        assert "YAML parse error" in result.error
        assert result.exception is not None

    def test_parse_block_with_custom_block_class(self) -> None:
        """Test parsing with custom Block class.

        This covers line 114 (extract_block_types usage).
        """

        class CustomMetadata(BaseMetadata):
            """Custom metadata with extra field."""

            custom_field: str = "default"

        class CustomContent(BaseContent):
            """Custom content."""

        custom_block = Block[CustomMetadata, CustomContent]

        syntax = MarkdownFrontmatterSyntax()
        candidate = BlockCandidate(syntax=syntax, start_line=1)
        candidate.metadata_lines = [
            "id: custom-1",
            "block_type: custom",
            "custom_field: value",
        ]
        candidate.content_lines = ["custom content"]

        result = syntax.parse_block(candidate, custom_block)

        assert result.success is True
        assert result.metadata is not None
        assert result.metadata.custom_field == "value"

    def test_parse_block_metadata_validation_error(self) -> None:
        """Test parse returns error on metadata validation failure.

        This covers lines 137-138.
        """

        class StrictMetadata(BaseMetadata):
            """Metadata requiring a specific field."""

            required_field: str  # Required, no default

        strict_block = Block[StrictMetadata, BaseContent]

        syntax = MarkdownFrontmatterSyntax()
        candidate = BlockCandidate(syntax=syntax, start_line=1)
        candidate.metadata_lines = [
            "id: test-1",
            "block_type: strict",
            # Missing required_field
        ]
        candidate.content_lines = ["content"]

        result = syntax.parse_block(candidate, strict_block)

        assert result.success is False
        assert "Metadata validation error" in result.error
        assert isinstance(result.exception, ValidationError)

    def test_parse_block_metadata_type_error(self) -> None:
        """Test parse returns error on metadata TypeError.

        This covers lines 139-140.
        """

        class BadMetadata(BaseMetadata):
            """Metadata that raises TypeError."""

            def __init__(self, **kwargs: object) -> None:
                if "trigger_error" in kwargs:
                    msg = "Intentional TypeError"
                    raise TypeError(msg)
                super().__init__(**kwargs)

        bad_block = Block[BadMetadata, BaseContent]

        syntax = MarkdownFrontmatterSyntax()
        candidate = BlockCandidate(syntax=syntax, start_line=1)
        candidate.metadata_lines = [
            "id: test-1",
            "block_type: bad",
            "trigger_error: true",
        ]
        candidate.content_lines = ["content"]

        result = syntax.parse_block(candidate, bad_block)

        assert result.success is False
        assert "Invalid metadata" in result.error

    def test_parse_block_content_validation_error(self) -> None:
        """Test parse returns error on content validation failure.

        This covers lines 148-149.
        """

        class StrictContent(BaseContent):
            """Content that fails validation in parse()."""

            required_data: str  # Required field

            @classmethod
            def parse(cls, raw: str) -> StrictContent:
                """Parse that always fails validation."""
                # Try to create without required field
                return cls(raw_content=raw)  # Missing required_data

        strict_content_block = Block[BaseMetadata, StrictContent]

        syntax = MarkdownFrontmatterSyntax()
        candidate = BlockCandidate(syntax=syntax, start_line=1)
        candidate.metadata_lines = ["id: test-1", "block_type: strict"]
        candidate.content_lines = ["content"]

        result = syntax.parse_block(candidate, strict_content_block)

        assert result.success is False
        assert "Content validation error" in result.error
        assert isinstance(result.exception, ValidationError)

    def test_parse_block_content_value_error(self) -> None:
        """Test parse returns error on content ValueError.

        This covers lines 150-151.
        """

        class ErrorContent(BaseContent):
            """Content that raises ValueError in parse()."""

            @classmethod
            def parse(cls, raw: str) -> ErrorContent:
                """Parse that raises ValueError."""
                msg = "Invalid content format"
                raise ValueError(msg)

        error_block = Block[BaseMetadata, ErrorContent]

        syntax = MarkdownFrontmatterSyntax()
        candidate = BlockCandidate(syntax=syntax, start_line=1)
        candidate.metadata_lines = ["id: test-1", "block_type: error"]
        candidate.content_lines = ["content"]

        result = syntax.parse_block(candidate, error_block)

        assert result.success is False
        assert "Invalid content" in result.error
        assert isinstance(result.exception, ValueError)


class TestMarkdownFrontmatterSyntaxValidateBlock:
    """Tests for MarkdownFrontmatterSyntax.validate_block()."""

    def test_validate_always_returns_true(self) -> None:
        """Test that validate_block always returns True."""
        syntax = MarkdownFrontmatterSyntax()
        mock_block = MagicMock()

        result = syntax.validate_block(mock_block)

        assert result is True


class TestMarkdownFrontmatterSyntaxIntegration:
    """Integration tests for MarkdownFrontmatterSyntax."""

    def test_full_block_workflow_with_frontmatter(self) -> None:
        """Test complete parsing workflow with frontmatter."""
        syntax = MarkdownFrontmatterSyntax(info_string="python")
        candidate = BlockCandidate(syntax=syntax, start_line=1)

        # Simulate line-by-line processing
        lines = [
            "---",
            "id: test-block",
            "block_type: python",
            "---",
            "def hello():",
            '    print("Hello")',
            "```",
        ]

        for line in lines:
            result = syntax.detect_line(line, candidate)
            if result.is_closing:
                break

        # Parse the complete block
        parse_result = syntax.parse_block(candidate)

        assert parse_result.success is True
        assert parse_result.metadata is not None
        assert parse_result.metadata.id == "test-block"
        assert parse_result.content is not None
        assert "def hello():" in parse_result.content.raw_content

    def test_full_block_workflow_without_frontmatter_fails(self) -> None:
        """Test that parsing without frontmatter fails due to missing required fields."""
        syntax = MarkdownFrontmatterSyntax(info_string="javascript")
        candidate = BlockCandidate(syntax=syntax, start_line=1)

        # Simulate line-by-line processing - content directly after fence
        lines = [
            "console.log('Hello');",
            "const x = 42;",
            "```",
        ]

        for line in lines:
            result = syntax.detect_line(line, candidate)
            if result.is_closing:
                break

        # Verify we moved to content directly
        assert candidate.current_section == SectionType.CONTENT
        assert len(candidate.content_lines) == 2

        # Parse the complete block - should fail because id and block_type are required
        parse_result = syntax.parse_block(candidate)

        assert parse_result.success is False
        assert "validation error" in parse_result.error.lower()

    def test_fence_pattern_matches_info_string_prefix(self) -> None:
        """Test that fence pattern matches info string as prefix."""
        syntax = MarkdownFrontmatterSyntax(info_string="py")

        # Should match with info string
        assert syntax.detect_line("```py").is_opening is True

        # Should also match longer info strings starting with py
        assert syntax.detect_line("```python").is_opening is True

    def test_custom_fence_syntax(self) -> None:
        """Test using custom fence characters."""
        syntax = MarkdownFrontmatterSyntax(fence="~~~")
        candidate = BlockCandidate(syntax=syntax, start_line=1)

        assert syntax.detect_line("~~~").is_opening is True

        candidate.current_section = SectionType.CONTENT
        assert syntax.detect_line("~~~", candidate).is_closing is True
