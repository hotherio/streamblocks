"""Tests for base syntax module."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
import yaml

from hother.streamblocks.core.types import BaseContent, BaseMetadata, DetectionResult, ParseResult
from hother.streamblocks.syntaxes.base import BaseSyntax, YAMLFrontmatterMixin


class TestYAMLFrontmatterMixinParseYamlMetadata:
    """Tests for YAMLFrontmatterMixin._parse_yaml_metadata()."""

    def test_parse_valid_yaml(self) -> None:
        """Test parsing valid YAML content."""
        mixin = YAMLFrontmatterMixin()
        lines = ["key: value", "number: 42"]

        result = mixin._parse_yaml_metadata(lines)

        assert result == {"key": "value", "number": 42}

    def test_parse_empty_list_returns_none(self) -> None:
        """Test that empty list returns None.

        This covers line 40.
        """
        mixin = YAMLFrontmatterMixin()

        result = mixin._parse_yaml_metadata([])

        assert result is None

    def test_parse_invalid_yaml_returns_none(self) -> None:
        """Test that invalid YAML returns None.

        This covers lines 44-45.
        """
        mixin = YAMLFrontmatterMixin()
        lines = ["[unclosed: bracket"]  # Invalid YAML

        result = mixin._parse_yaml_metadata(lines)

        assert result is None

    def test_parse_yaml_with_only_null_returns_empty_dict(self) -> None:
        """Test that YAML parsing null returns empty dict."""
        mixin = YAMLFrontmatterMixin()
        lines = [""]  # Empty YAML content

        result = mixin._parse_yaml_metadata(lines)

        # Empty content parses to None, but we return {} instead
        assert result == {}

    def test_parse_nested_yaml(self) -> None:
        """Test parsing nested YAML structures."""
        mixin = YAMLFrontmatterMixin()
        lines = [
            "parent:",
            "  child: value",
            "  nested:",
            "    deep: data",
        ]

        result = mixin._parse_yaml_metadata(lines)

        assert result == {
            "parent": {
                "child": "value",
                "nested": {"deep": "data"},
            }
        }

    def test_parse_yaml_list(self) -> None:
        """Test parsing YAML with list values."""
        mixin = YAMLFrontmatterMixin()
        lines = [
            "items:",
            "  - one",
            "  - two",
            "  - three",
        ]

        result = mixin._parse_yaml_metadata(lines)

        assert result == {"items": ["one", "two", "three"]}


class TestYAMLFrontmatterMixinParseYamlMetadataStrict:
    """Tests for YAMLFrontmatterMixin._parse_yaml_metadata_strict()."""

    def test_parse_valid_yaml(self) -> None:
        """Test parsing valid YAML content."""
        mixin = YAMLFrontmatterMixin()
        lines = ["key: value", "number: 42"]

        result, error = mixin._parse_yaml_metadata_strict(lines)

        assert result == {"key": "value", "number": 42}
        assert error is None

    def test_parse_empty_list_returns_empty_dict_no_error(self) -> None:
        """Test that empty list returns empty dict and no error.

        This covers line 59.
        """
        mixin = YAMLFrontmatterMixin()

        result, error = mixin._parse_yaml_metadata_strict([])

        assert result == {}
        assert error is None

    def test_parse_invalid_yaml_returns_exception(self) -> None:
        """Test that invalid YAML returns the exception.

        This covers lines 63-64.
        """
        mixin = YAMLFrontmatterMixin()
        lines = ["[unclosed: bracket"]  # Invalid YAML

        result, error = mixin._parse_yaml_metadata_strict(lines)

        assert result == {}
        assert error is not None
        assert isinstance(error, yaml.YAMLError)

    def test_parse_yaml_with_only_null_returns_empty_dict(self) -> None:
        """Test that YAML parsing null returns empty dict."""
        mixin = YAMLFrontmatterMixin()
        lines = [""]  # Empty YAML content

        result, error = mixin._parse_yaml_metadata_strict(lines)

        # Empty content parses to None, but we return {} instead
        assert result == {}
        assert error is None

    def test_parse_multiline_error_returns_correct_exception(self) -> None:
        """Test that multiline invalid YAML returns proper exception."""
        mixin = YAMLFrontmatterMixin()
        lines = [
            "key: [value",  # Opening bracket without close
            "another: line",  # This makes the bracket unclosed across lines
        ]

        result, error = mixin._parse_yaml_metadata_strict(lines)

        assert result == {}
        assert error is not None
        assert isinstance(error, yaml.YAMLError)


class ConcreteSyntax(BaseSyntax):
    """Concrete implementation of BaseSyntax for testing."""

    def detect_line(self, line: str, candidate: Any = None) -> DetectionResult:
        """Minimal detect_line implementation."""
        if line.startswith("!!"):
            return DetectionResult(is_opening=True)
        if line.startswith("!!end"):
            return DetectionResult(is_closing=True)
        return DetectionResult()

    def should_accumulate_metadata(self, candidate: Any) -> bool:
        """Minimal should_accumulate_metadata implementation."""
        return False

    def extract_block_type(self, candidate: Any) -> str | None:
        """Minimal extract_block_type implementation."""
        return "test"

    def parse_block(
        self, candidate: Any, block_class: type[Any] | None = None
    ) -> ParseResult[BaseMetadata, BaseContent]:
        """Minimal parse_block implementation."""
        return ParseResult(success=False, error="Not implemented")


class TestBaseSyntaxDefaultMethods:
    """Tests for BaseSyntax default method implementations."""

    def test_validate_block_returns_true_by_default(self) -> None:
        """Test that default validate_block returns True.

        This covers line 176.
        """
        syntax = ConcreteSyntax()
        mock_block = MagicMock()

        result = syntax.validate_block(mock_block)

        assert result is True

    def test_parse_metadata_early_returns_none_by_default(self) -> None:
        """Test that default parse_metadata_early returns None."""
        syntax = ConcreteSyntax()
        mock_candidate = MagicMock()

        result = syntax.parse_metadata_early(mock_candidate)

        assert result is None

    def test_parse_content_early_returns_none_by_default(self) -> None:
        """Test that default parse_content_early returns None."""
        syntax = ConcreteSyntax()
        mock_candidate = MagicMock()

        result = syntax.parse_content_early(mock_candidate)

        assert result is None


class TestBaseSyntaxAbstractMethods:
    """Tests verifying abstract method requirements."""

    def test_cannot_instantiate_base_syntax_directly(self) -> None:
        """Test that BaseSyntax cannot be instantiated directly."""
        with pytest.raises(TypeError, match="abstract"):
            BaseSyntax()  # type: ignore[abstract]

    def test_subclass_must_implement_detect_line(self) -> None:
        """Test that subclass must implement detect_line."""

        class IncompleteWithoutDetect(BaseSyntax):
            def should_accumulate_metadata(self, candidate: Any) -> bool:
                return False

            def extract_block_type(self, candidate: Any) -> str | None:
                return "test"

            def parse_block(
                self, candidate: Any, block_class: type[Any] | None = None
            ) -> ParseResult[BaseMetadata, BaseContent]:
                return ParseResult(success=False, error="Not implemented")

        with pytest.raises(TypeError, match="abstract"):
            IncompleteWithoutDetect()  # type: ignore[abstract]

    def test_subclass_must_implement_should_accumulate_metadata(self) -> None:
        """Test that subclass must implement should_accumulate_metadata."""

        class IncompleteWithoutShouldAccumulate(BaseSyntax):
            def detect_line(self, line: str, candidate: Any = None) -> DetectionResult:
                return DetectionResult()

            def extract_block_type(self, candidate: Any) -> str | None:
                return "test"

            def parse_block(
                self, candidate: Any, block_class: type[Any] | None = None
            ) -> ParseResult[BaseMetadata, BaseContent]:
                return ParseResult(success=False, error="Not implemented")

        with pytest.raises(TypeError, match="abstract"):
            IncompleteWithoutShouldAccumulate()  # type: ignore[abstract]

    def test_subclass_must_implement_extract_block_type(self) -> None:
        """Test that subclass must implement extract_block_type."""

        class IncompleteWithoutExtract(BaseSyntax):
            def detect_line(self, line: str, candidate: Any = None) -> DetectionResult:
                return DetectionResult()

            def should_accumulate_metadata(self, candidate: Any) -> bool:
                return False

            def parse_block(
                self, candidate: Any, block_class: type[Any] | None = None
            ) -> ParseResult[BaseMetadata, BaseContent]:
                return ParseResult(success=False, error="Not implemented")

        with pytest.raises(TypeError, match="abstract"):
            IncompleteWithoutExtract()  # type: ignore[abstract]

    def test_subclass_must_implement_parse_block(self) -> None:
        """Test that subclass must implement parse_block."""

        class IncompleteWithoutParse(BaseSyntax):
            def detect_line(self, line: str, candidate: Any = None) -> DetectionResult:
                return DetectionResult()

            def should_accumulate_metadata(self, candidate: Any) -> bool:
                return False

            def extract_block_type(self, candidate: Any) -> str | None:
                return "test"

        with pytest.raises(TypeError, match="abstract"):
            IncompleteWithoutParse()  # type: ignore[abstract]


class TestConcreteSyntaxImplementation:
    """Tests for the concrete test syntax implementation."""

    def test_concrete_syntax_can_be_instantiated(self) -> None:
        """Test that complete concrete implementation can be instantiated."""
        syntax = ConcreteSyntax()

        assert syntax is not None

    def test_concrete_syntax_detect_line_works(self) -> None:
        """Test that concrete detect_line implementation works."""
        syntax = ConcreteSyntax()

        result = syntax.detect_line("!!block")

        assert result.is_opening is True

    def test_concrete_syntax_non_opening_line(self) -> None:
        """Test that non-opening line returns empty detection result."""
        syntax = ConcreteSyntax()

        result = syntax.detect_line("regular text")

        assert result.is_opening is False
        assert result.is_closing is False

    def test_concrete_syntax_extract_block_type(self) -> None:
        """Test that concrete extract_block_type works."""
        syntax = ConcreteSyntax()
        mock_candidate = MagicMock()

        result = syntax.extract_block_type(mock_candidate)

        assert result == "test"
