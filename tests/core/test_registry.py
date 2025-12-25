"""Tests for core registry module."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from hother.streamblocks.core.models import Block, ExtractedBlock
from hother.streamblocks.core.registry import (
    MetadataValidationFailureMode,
    Registry,
    ValidationResult,
)
from hother.streamblocks.core.types import BaseContent, BaseMetadata
from hother.streamblocks.syntaxes.delimiter import DelimiterPreambleSyntax


@pytest.fixture
def syntax() -> DelimiterPreambleSyntax:
    """Create a default syntax for tests."""
    return DelimiterPreambleSyntax()


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_default_values(self) -> None:
        """Test default values for ValidationResult."""
        result = ValidationResult()

        assert result.passed is True
        assert result.error is None

    def test_success_factory(self) -> None:
        """Test ValidationResult.success() factory method."""
        result = ValidationResult.success()

        assert result.passed is True
        assert result.error is None

    def test_failure_factory(self) -> None:
        """Test ValidationResult.failure() factory method."""
        result = ValidationResult.failure("Test error")

        assert result.passed is False
        assert result.error == "Test error"


class TestRegistryInit:
    """Tests for Registry initialization."""

    def test_basic_initialization(self, syntax: DelimiterPreambleSyntax) -> None:
        """Test basic registry initialization."""
        registry = Registry(syntax=syntax)

        assert registry.syntax is syntax
        assert registry.metadata_failure_mode == MetadataValidationFailureMode.ABORT_BLOCK

    def test_custom_metadata_failure_mode(self, syntax: DelimiterPreambleSyntax) -> None:
        """Test registry with custom metadata failure mode."""
        registry = Registry(
            syntax=syntax,
            metadata_failure_mode=MetadataValidationFailureMode.CONTINUE,
        )

        assert registry.metadata_failure_mode == MetadataValidationFailureMode.CONTINUE

    def test_custom_logger(self, syntax: DelimiterPreambleSyntax) -> None:
        """Test registry with custom logger."""
        mock_logger = MagicMock()
        registry = Registry(syntax=syntax, logger=mock_logger)

        assert registry.logger is mock_logger

    def test_bulk_registration(self, syntax: DelimiterPreambleSyntax) -> None:
        """Test bulk block registration in __init__.

        This covers lines 107-108.
        """

        class TestMetadata(BaseMetadata):
            pass

        class TestContent(BaseContent):
            pass

        test_block = Block[TestMetadata, TestContent]

        class AnotherMetadata(BaseMetadata):
            pass

        class AnotherContent(BaseContent):
            pass

        another_block = Block[AnotherMetadata, AnotherContent]

        registry = Registry(
            syntax=syntax,
            blocks={
                "test": test_block,
                "another": another_block,
            },
        )

        assert registry.get_block_class("test") is test_block
        assert registry.get_block_class("another") is another_block


class TestRegistryRegister:
    """Tests for Registry.register() method."""

    def test_register_block_class(self, syntax: DelimiterPreambleSyntax) -> None:
        """Test registering a block class."""

        class TestMetadata(BaseMetadata):
            pass

        class TestContent(BaseContent):
            pass

        test_block = Block[TestMetadata, TestContent]

        registry = Registry(syntax=syntax)
        registry.register("test", test_block)

        assert registry.get_block_class("test") is test_block

    def test_register_with_validators(self, syntax: DelimiterPreambleSyntax) -> None:
        """Test registering a block class with validators.

        This covers lines 139-140.
        """

        class TestMetadata(BaseMetadata):
            pass

        class TestContent(BaseContent):
            pass

        test_block = Block[TestMetadata, TestContent]

        def validator1(block: ExtractedBlock[Any, Any]) -> bool:
            return True

        def validator2(block: ExtractedBlock[Any, Any]) -> bool:
            return True

        registry = Registry(syntax=syntax)
        registry.register("test", test_block, validators=[validator1, validator2])

        # Validators should be registered
        assert "test" in registry._validators
        assert len(registry._validators["test"]) == 2

    def test_get_block_class_not_found(self, syntax: DelimiterPreambleSyntax) -> None:
        """Test getting a block class that doesn't exist."""
        registry = Registry(syntax=syntax)

        result = registry.get_block_class("nonexistent")

        assert result is None


class TestRegistryAddValidator:
    """Tests for Registry.add_validator() method."""

    def test_add_validator_to_new_block_type(self, syntax: DelimiterPreambleSyntax) -> None:
        """Test adding validator to a new block type.

        This covers lines 164-168.
        """

        def my_validator(block: ExtractedBlock[Any, Any]) -> bool:
            return True

        registry = Registry(syntax=syntax)
        registry.add_validator("new_type", my_validator)

        assert "new_type" in registry._validators
        assert my_validator in registry._validators["new_type"]

    def test_add_multiple_validators(self, syntax: DelimiterPreambleSyntax) -> None:
        """Test adding multiple validators to the same block type."""

        def validator1(block: ExtractedBlock[Any, Any]) -> bool:
            return True

        def validator2(block: ExtractedBlock[Any, Any]) -> bool:
            return True

        registry = Registry(syntax=syntax)
        registry.add_validator("test", validator1)
        registry.add_validator("test", validator2)

        assert len(registry._validators["test"]) == 2


class TestRegistryValidateBlock:
    """Tests for Registry.validate_block() method."""

    def test_validate_block_with_none_block_type(self, syntax: DelimiterPreambleSyntax) -> None:
        """Test validating a block with None block_type.

        BaseMetadata always has block_type attribute, but it can be None.
        This covers line 188-189.
        """
        registry = Registry(syntax=syntax)

        # Create a mock block with block_type = None
        mock_block = MagicMock(spec=ExtractedBlock)
        mock_metadata = MagicMock()
        mock_metadata.block_type = None
        mock_block.metadata = mock_metadata

        result = registry.validate_block(mock_block)

        assert result is True

    def test_validate_block_with_validators(self, syntax: DelimiterPreambleSyntax) -> None:
        """Test validating a block with registered validators."""

        def passing_validator(block: ExtractedBlock[Any, Any]) -> bool:
            return True

        registry = Registry(syntax=syntax)
        registry.add_validator("test", passing_validator)

        mock_block = MagicMock(spec=ExtractedBlock)
        mock_metadata = MagicMock()
        mock_metadata.block_type = "test"
        mock_block.metadata = mock_metadata

        result = registry.validate_block(mock_block)

        assert result is True

    def test_validate_block_with_failing_validator(self, syntax: DelimiterPreambleSyntax) -> None:
        """Test validating a block with a failing validator."""

        def failing_validator(block: ExtractedBlock[Any, Any]) -> bool:
            return False

        registry = Registry(syntax=syntax)
        registry.add_validator("test", failing_validator)

        mock_block = MagicMock(spec=ExtractedBlock)
        mock_metadata = MagicMock()
        mock_metadata.block_type = "test"
        mock_block.metadata = mock_metadata

        result = registry.validate_block(mock_block)

        assert result is False

    def test_validate_block_without_validators(self, syntax: DelimiterPreambleSyntax) -> None:
        """Test validating a block with no validators registered."""
        registry = Registry(syntax=syntax)

        mock_block = MagicMock(spec=ExtractedBlock)
        mock_metadata = MagicMock()
        mock_metadata.block_type = "test"
        mock_block.metadata = mock_metadata

        result = registry.validate_block(mock_block)

        assert result is True


class TestRegistryMetadataValidation:
    """Tests for Registry metadata validation methods."""

    def test_add_metadata_validator(self, syntax: DelimiterPreambleSyntax) -> None:
        """Test adding a metadata validator."""

        def metadata_validator(raw: str, parsed: dict[str, Any] | None) -> ValidationResult:
            return ValidationResult.success()

        registry = Registry(syntax=syntax)
        registry.add_metadata_validator("test", metadata_validator)

        assert "test" in registry._metadata_validators
        assert metadata_validator in registry._metadata_validators["test"]

    def test_add_multiple_metadata_validators_same_block_type(self, syntax: DelimiterPreambleSyntax) -> None:
        """Test adding multiple metadata validators to the same block type.

        This covers branch 214->216 where block_type IS already in _metadata_validators.
        """

        def validator1(raw: str, parsed: dict[str, Any] | None) -> ValidationResult:
            return ValidationResult.success()

        def validator2(raw: str, parsed: dict[str, Any] | None) -> ValidationResult:
            return ValidationResult.success()

        registry = Registry(syntax=syntax)
        # First validator - creates the list (line 215-216)
        registry.add_metadata_validator("test", validator1)
        # Second validator - skips list creation (branch 214->216)
        registry.add_metadata_validator("test", validator2)

        assert len(registry._metadata_validators["test"]) == 2
        assert validator1 in registry._metadata_validators["test"]
        assert validator2 in registry._metadata_validators["test"]

    def test_validate_metadata_no_validators(self, syntax: DelimiterPreambleSyntax) -> None:
        """Test validating metadata with no validators returns success."""
        registry = Registry(syntax=syntax)

        result = registry.validate_metadata("test", "raw", {"key": "value"})

        assert result.passed is True

    def test_validate_metadata_passing(self, syntax: DelimiterPreambleSyntax) -> None:
        """Test validating metadata with passing validator."""

        def passing_validator(raw: str, parsed: dict[str, Any] | None) -> ValidationResult:
            return ValidationResult.success()

        registry = Registry(syntax=syntax)
        registry.add_metadata_validator("test", passing_validator)

        result = registry.validate_metadata("test", "raw", {"key": "value"})

        assert result.passed is True

    def test_validate_metadata_failing(self, syntax: DelimiterPreambleSyntax) -> None:
        """Test validating metadata with failing validator."""

        def failing_validator(raw: str, parsed: dict[str, Any] | None) -> ValidationResult:
            return ValidationResult.failure("Invalid metadata")

        registry = Registry(syntax=syntax)
        registry.add_metadata_validator("test", failing_validator)

        result = registry.validate_metadata("test", "raw", {"key": "value"})

        assert result.passed is False
        assert result.error == "Invalid metadata"


class TestRegistryContentValidation:
    """Tests for Registry content validation methods."""

    def test_add_content_validator(self, syntax: DelimiterPreambleSyntax) -> None:
        """Test adding a content validator."""

        def content_validator(raw: str, parsed: dict[str, Any] | None) -> ValidationResult:
            return ValidationResult.success()

        registry = Registry(syntax=syntax)
        registry.add_content_validator("test", content_validator)

        assert "test" in registry._content_validators
        assert content_validator in registry._content_validators["test"]

    def test_validate_content_no_validators(self, syntax: DelimiterPreambleSyntax) -> None:
        """Test validating content with no validators returns success.

        This covers line 315.
        """
        registry = Registry(syntax=syntax)

        result = registry.validate_content("test", "raw content", {"key": "value"})

        assert result.passed is True

    def test_validate_content_passing(self, syntax: DelimiterPreambleSyntax) -> None:
        """Test validating content with passing validator."""

        def passing_validator(raw: str, parsed: dict[str, Any] | None) -> ValidationResult:
            return ValidationResult.success()

        registry = Registry(syntax=syntax)
        registry.add_content_validator("test", passing_validator)

        result = registry.validate_content("test", "raw content", {"key": "value"})

        assert result.passed is True

    def test_validate_content_failing(self, syntax: DelimiterPreambleSyntax) -> None:
        """Test validating content with failing validator."""

        def failing_validator(raw: str, parsed: dict[str, Any] | None) -> ValidationResult:
            return ValidationResult.failure("Invalid content")

        registry = Registry(syntax=syntax)
        registry.add_content_validator("test", failing_validator)

        result = registry.validate_content("test", "raw content", {"key": "value"})

        assert result.passed is False
        assert result.error == "Invalid content"

    def test_validate_content_multiple_validators_first_fails(self, syntax: DelimiterPreambleSyntax) -> None:
        """Test that validation stops on first failure."""

        def failing_validator(raw: str, parsed: dict[str, Any] | None) -> ValidationResult:
            return ValidationResult.failure("First failed")

        def passing_validator(raw: str, parsed: dict[str, Any] | None) -> ValidationResult:
            return ValidationResult.success()

        registry = Registry(syntax=syntax)
        registry.add_content_validator("test", failing_validator)
        registry.add_content_validator("test", passing_validator)

        result = registry.validate_content("test", "raw", None)

        assert result.passed is False
        assert result.error == "First failed"
