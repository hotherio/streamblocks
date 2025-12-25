"""Tests for syntaxes/models.py."""

from __future__ import annotations

from typing import Any

import pytest

from hother.streamblocks.core.types import BaseContent, BaseMetadata, DetectionResult, ParseResult
from hother.streamblocks.syntaxes.delimiter import (
    DelimiterFrontmatterSyntax,
    DelimiterPreambleSyntax,
)
from hother.streamblocks.syntaxes.markdown import MarkdownFrontmatterSyntax
from hother.streamblocks.syntaxes.models import Syntax, get_syntax_instance


class TestSyntaxEnum:
    """Tests for Syntax enum."""

    def test_syntax_enum_members(self) -> None:
        """Test all Syntax enum members exist."""
        assert Syntax.DELIMITER_FRONTMATTER is not None
        assert Syntax.DELIMITER_PREAMBLE is not None
        assert Syntax.MARKDOWN_FRONTMATTER is not None

    def test_syntax_enum_is_str_enum(self) -> None:
        """Test Syntax members are strings."""
        assert isinstance(Syntax.DELIMITER_PREAMBLE, str)

    def test_syntax_enum_values_are_unique(self) -> None:
        """Test all enum values are unique."""
        values = [member.value for member in Syntax]
        assert len(values) == len(set(values))


class TestGetSyntaxInstanceWithEnums:
    """Tests for get_syntax_instance() with Syntax enum values."""

    def test_delimiter_frontmatter(self) -> None:
        """Test getting DelimiterFrontmatterSyntax from enum."""
        syntax = get_syntax_instance(Syntax.DELIMITER_FRONTMATTER)

        assert isinstance(syntax, DelimiterFrontmatterSyntax)

    def test_delimiter_preamble(self) -> None:
        """Test getting DelimiterPreambleSyntax from enum."""
        syntax = get_syntax_instance(Syntax.DELIMITER_PREAMBLE)

        assert isinstance(syntax, DelimiterPreambleSyntax)

    def test_markdown_frontmatter(self) -> None:
        """Test getting MarkdownFrontmatterSyntax from enum."""
        syntax = get_syntax_instance(Syntax.MARKDOWN_FRONTMATTER)

        assert isinstance(syntax, MarkdownFrontmatterSyntax)

    def test_all_enum_values_return_valid_syntax(self) -> None:
        """Test that all enum values return a valid syntax instance."""
        for member in Syntax:
            syntax = get_syntax_instance(member)

            # All returned syntaxes should have required methods
            assert hasattr(syntax, "detect_line")
            assert hasattr(syntax, "parse_block")


class TestGetSyntaxInstanceWithCustomSyntax:
    """Tests for get_syntax_instance() with custom syntax instances."""

    def test_custom_syntax_is_returned_as_is(self) -> None:
        """Test that a custom syntax instance is returned unchanged."""
        custom_syntax = DelimiterPreambleSyntax()

        result = get_syntax_instance(custom_syntax)

        assert result is custom_syntax

    def test_custom_frontmatter_syntax(self) -> None:
        """Test custom DelimiterFrontmatterSyntax."""
        custom_syntax = DelimiterFrontmatterSyntax(
            start_delimiter="<<<START>>>",
            end_delimiter="<<<END>>>",
        )

        result = get_syntax_instance(custom_syntax)

        assert result is custom_syntax
        assert result.start_delimiter == "<<<START>>>"

    def test_custom_preamble_syntax(self) -> None:
        """Test custom DelimiterPreambleSyntax with custom delimiter."""
        custom_syntax = DelimiterPreambleSyntax(delimiter="@@")

        result = get_syntax_instance(custom_syntax)

        assert result is custom_syntax
        assert result.delimiter == "@@"

    def test_custom_basesyntax_subclass_is_accepted(self) -> None:
        """Test that a proper BaseSyntax subclass is accepted."""
        from hother.streamblocks.syntaxes.base import BaseSyntax

        class CustomSyntax(BaseSyntax):
            """Custom syntax implementation."""

            def detect_line(self, line: str, candidate: Any = None) -> DetectionResult:
                return DetectionResult()

            def should_accumulate_metadata(self, candidate: Any) -> bool:
                return False

            def extract_block_type(self, candidate: Any) -> str | None:
                return "custom"

            def parse_block(
                self, candidate: Any, block_class: type | None = None
            ) -> ParseResult[BaseMetadata, BaseContent]:
                return ParseResult(success=False, error="Not implemented")

        custom = CustomSyntax()
        result = get_syntax_instance(custom)

        assert result is custom

    def test_duck_typed_object_is_rejected(self) -> None:
        """Test that duck-typed objects without BaseSyntax inheritance are rejected.

        This ensures proper validation - users must inherit from BaseSyntax
        to get all 4 abstract methods enforced at class definition time.
        """

        class DuckTypedSyntax:
            """Has methods but doesn't inherit from BaseSyntax."""

            def detect_line(self, line: str, candidate: Any = None) -> DetectionResult:
                return DetectionResult()

            def parse_block(
                self, candidate: Any, block_class: type | None = None
            ) -> ParseResult[BaseMetadata, BaseContent]:
                return ParseResult(success=False, error="Not implemented")

        with pytest.raises(TypeError, match="Expected Syntax enum or BaseSyntax instance"):
            get_syntax_instance(DuckTypedSyntax())  # type: ignore[arg-type]


class TestGetSyntaxInstanceErrors:
    """Tests for get_syntax_instance() error cases."""

    def test_invalid_string_raises_type_error(self) -> None:
        """Test that a plain string raises TypeError."""
        with pytest.raises(TypeError, match="Expected Syntax enum or BaseSyntax instance"):
            get_syntax_instance("invalid")  # type: ignore[arg-type]

    def test_invalid_number_raises_type_error(self) -> None:
        """Test that a number raises TypeError."""
        with pytest.raises(TypeError, match="Expected Syntax enum or BaseSyntax instance"):
            get_syntax_instance(123)  # type: ignore[arg-type]

    def test_invalid_none_raises_type_error(self) -> None:
        """Test that None raises TypeError."""
        with pytest.raises(TypeError, match="Expected Syntax enum or BaseSyntax instance"):
            get_syntax_instance(None)  # type: ignore[arg-type]

    def test_invalid_dict_raises_type_error(self) -> None:
        """Test that a dict raises TypeError."""
        with pytest.raises(TypeError, match="Expected Syntax enum or BaseSyntax instance"):
            get_syntax_instance({"detect_line": True})  # type: ignore[arg-type]

    def test_incomplete_object_raises_type_error(self) -> None:
        """Test that an object without required methods raises TypeError."""

        class IncompleteSyntax:
            def detect_line(self, line: str) -> DetectionResult:
                return DetectionResult()

            # Missing parse_block method

        with pytest.raises(TypeError, match="Expected Syntax enum or BaseSyntax instance"):
            get_syntax_instance(IncompleteSyntax())  # type: ignore[arg-type]

    def test_error_message_includes_type_info(self) -> None:
        """Test that error message includes the type of invalid input."""
        with pytest.raises(TypeError) as exc_info:
            get_syntax_instance([1, 2, 3])  # type: ignore[arg-type]

        assert "list" in str(exc_info.value)


class TestGetSyntaxInstanceReturnedSyntaxes:
    """Tests for returned syntax instances."""

    def test_returned_delimiter_preamble_is_functional(self) -> None:
        """Test that returned DelimiterPreambleSyntax works correctly."""
        syntax = get_syntax_instance(Syntax.DELIMITER_PREAMBLE)

        # Should detect opening marker
        result = syntax.detect_line("!!myblock:file")
        assert result.is_opening is True

    def test_returned_delimiter_frontmatter_is_functional(self) -> None:
        """Test that returned DelimiterFrontmatterSyntax works correctly."""
        syntax = get_syntax_instance(Syntax.DELIMITER_FRONTMATTER)

        # Should detect opening marker
        result = syntax.detect_line("!!start")
        assert result.is_opening is True

    def test_returned_markdown_frontmatter_is_functional(self) -> None:
        """Test that returned MarkdownFrontmatterSyntax works correctly."""
        syntax = get_syntax_instance(Syntax.MARKDOWN_FRONTMATTER)

        # Should detect opening marker (code fence)
        result = syntax.detect_line("```python")
        assert result.is_opening is True


class TestSyntaxEnumIntegration:
    """Integration tests for Syntax enum with Registry."""

    def test_syntax_enum_works_with_registry(self) -> None:
        """Test using Syntax enum with Registry via get_syntax_instance."""
        from hother.streamblocks import Registry

        syntax = get_syntax_instance(Syntax.DELIMITER_PREAMBLE)
        registry = Registry(syntax=syntax)

        assert registry.syntax is syntax
