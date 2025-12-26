"""Type-specific registry for StreamBlocks."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from hother.streamblocks.core._logger import StdlibLoggerAdapter
from hother.streamblocks.syntaxes.factory import get_syntax_instance
from hother.streamblocks.syntaxes.models import Syntax

if TYPE_CHECKING:
    from hother.streamblocks.core._logger import Logger
    from hother.streamblocks.core.models import Block, ExtractedBlock
    from hother.streamblocks.syntaxes.base import BaseSyntax


# Type aliases for better documentation
# Note: Using type aliases instead of NewType to avoid requiring explicit wrapping
# throughout the codebase where plain strings are used as block types
type BlockType = str
type SyntaxName = str
type ValidatorFunc = Callable[[ExtractedBlock[Any, Any]], bool]
type MetadataValidatorFunc = Callable[[str, dict[str, Any] | None], ValidationResult]
type ContentValidatorFunc = Callable[[str, dict[str, Any] | None], ValidationResult]


class MetadataValidationFailureMode(StrEnum):
    """Behavior when metadata validation fails."""

    ABORT_BLOCK = "abort_block"  # Emit BlockErrorEvent immediately
    CONTINUE = "continue"  # Continue with warning, process content
    SKIP_CONTENT = "skip_content"  # Skip content, emit partial block


@dataclass
class ValidationResult:
    """Result from section validation.

    Attributes:
        passed: Whether validation succeeded
        error: Error message if validation failed
    """

    passed: bool = True
    error: str | None = None

    @classmethod
    def success(cls) -> ValidationResult:
        """Create a successful validation result."""
        return cls(passed=True)

    @classmethod
    def failure(cls, error: str) -> ValidationResult:
        """Create a failed validation result."""
        return cls(passed=False, error=error)


class Registry:
    """Type-specific registry for a single syntax type.

    This registry holds exactly one syntax instance and maps block types to block classes.

    Example:
        >>> syntax = DelimiterPreambleSyntax(name="my_syntax")
        >>> registry = Registry(syntax)
        >>> registry.register("files_operations", FileOperations, validators=[my_validator])
        >>> registry.register("patch", Patch)

        Or with bulk registration:
        >>> registry = Registry(
        ...     syntax=syntax,
        ...     blocks={
        ...         "files_operations": FileOperations,
        ...         "patch": Patch,
        ...     }
        ... )
        >>> registry.add_validator("files_operations", my_validator)
    """

    def __init__(
        self,
        *,
        syntax: Syntax | BaseSyntax = Syntax.DELIMITER_PREAMBLE,
        logger: Logger | None = None,
        blocks: dict[str, type[Block[Any, Any]]] | None = None,
        metadata_failure_mode: MetadataValidationFailureMode = MetadataValidationFailureMode.ABORT_BLOCK,
    ) -> None:
        """Initialize registry with a single syntax instance.

        Args:
            syntax: The syntax instance for this registry.
                   Defaults to Syntax.DELIMITER_PREAMBLE.
            logger: Optional logger (any object with debug/info/warning/error/exception methods).
                   Defaults to stdlib logging.getLogger(__name__)
            blocks: Optional dict of block_type -> block_class for bulk registration
            metadata_failure_mode: Behavior when metadata validation fails
        """
        self._syntax = get_syntax_instance(syntax=syntax)
        self._block_classes: dict[BlockType, type[Block[Any, Any]]] = {}
        self._validators: dict[BlockType, list[ValidatorFunc]] = {}
        self._metadata_validators: dict[BlockType, list[MetadataValidatorFunc]] = {}
        self._content_validators: dict[BlockType, list[ContentValidatorFunc]] = {}
        self._metadata_failure_mode = metadata_failure_mode
        self.logger = logger or StdlibLoggerAdapter(logging.getLogger(__name__))

        # Bulk register blocks if provided
        if blocks:
            for block_type, block_class in blocks.items():
                self.register(block_type, block_class)

    @property
    def syntax(self) -> BaseSyntax:
        """Get the syntax instance."""
        return self._syntax

    def register(
        self,
        name: str,
        block_class: type[Block[Any, Any]],
        validators: list[ValidatorFunc] | None = None,
    ) -> None:
        """Register a block class for a block type.

        Args:
            name: Block type name (e.g., "files_operations", "patch")
            block_class: Block class inheriting from Block[M, C]
            validators: Optional list of validator functions for this block type
        """
        self._block_classes[name] = block_class

        self.logger.debug(
            "block_type_registered",
            block_type=name,
            block_class=block_class.__name__,
            has_validators=validators is not None and len(validators) > 0,
        )

        # Add validators if provided
        if validators:
            for validator in validators:
                self.add_validator(name, validator)

    def get_block_class(self, block_type: str) -> type[Block[Any, Any]] | None:
        """Get the block class for a given block type.

        Args:
            block_type: The block type to look up

        Returns:
            The registered block class, or None if not found
        """
        return self._block_classes.get(block_type)

    def add_validator(
        self,
        block_type: BlockType,
        validator: ValidatorFunc,
    ) -> None:
        """Add a validator for a block type.

        Args:
            block_type: Type of block to validate
            validator: Function that validates a block
        """
        if block_type not in self._validators:
            self._validators[block_type] = []
        self._validators[block_type].append(validator)

        self.logger.debug(
            "validator_added",
            block_type=block_type,
            validator_name=validator.__name__,
            total_validators=len(self._validators[block_type]),
        )

    def validate_block(
        self,
        block: ExtractedBlock[Any, Any],
    ) -> bool:
        """Run all validators for a block.

        Args:
            block: Extracted block to validate

        Returns:
            True if all validators pass
        """
        # block.metadata is BaseMetadata which always has block_type
        block_type = block.metadata.block_type
        if not block_type:
            return True

        validators = self._validators.get(block_type, [])
        return all(v(block) for v in validators)

    @property
    def metadata_failure_mode(self) -> MetadataValidationFailureMode:
        """Get the metadata validation failure mode."""
        return self._metadata_failure_mode

    def add_metadata_validator(
        self,
        block_type: BlockType,
        validator: MetadataValidatorFunc,
    ) -> None:
        """Add an early metadata validator for a block type.

        Metadata validators are called when the metadata section completes,
        before content accumulation begins. They receive the raw metadata
        string and the parsed metadata dict.

        Args:
            block_type: Type of block to validate
            validator: Function that validates metadata and returns ValidationResult
        """
        if block_type not in self._metadata_validators:
            self._metadata_validators[block_type] = []
        self._metadata_validators[block_type].append(validator)

        self.logger.debug(
            "metadata_validator_added",
            block_type=block_type,
            validator_name=validator.__name__,
            total_validators=len(self._metadata_validators[block_type]),
        )

    def add_content_validator(
        self,
        block_type: BlockType,
        validator: ContentValidatorFunc,
    ) -> None:
        """Add an early content validator for a block type.

        Content validators are called when the content section completes,
        before the final BlockEndEvent. They receive the raw content
        string and the parsed content dict.

        Args:
            block_type: Type of block to validate
            validator: Function that validates content and returns ValidationResult
        """
        if block_type not in self._content_validators:
            self._content_validators[block_type] = []
        self._content_validators[block_type].append(validator)

        self.logger.debug(
            "content_validator_added",
            block_type=block_type,
            validator_name=validator.__name__,
            total_validators=len(self._content_validators[block_type]),
        )

    def validate_metadata(
        self,
        block_type: str,
        raw_metadata: str,
        parsed_metadata: dict[str, Any] | None,
    ) -> ValidationResult:
        """Run all metadata validators for a block type.

        Args:
            block_type: Type of block being validated
            raw_metadata: Raw metadata string
            parsed_metadata: Parsed metadata dict (if available)

        Returns:
            ValidationResult with combined results from all validators
        """
        validators = self._metadata_validators.get(block_type, [])
        if not validators:
            return ValidationResult.success()

        for validator in validators:
            result = validator(raw_metadata, parsed_metadata)
            if not result.passed:
                self.logger.debug(
                    "metadata_validation_failed",
                    block_type=block_type,
                    validator_name=validator.__name__,
                    error=result.error,
                )
                return result

        return ValidationResult.success()

    def validate_content(
        self,
        block_type: str,
        raw_content: str,
        parsed_content: dict[str, Any] | None,
    ) -> ValidationResult:
        """Run all content validators for a block type.

        Args:
            block_type: Type of block being validated
            raw_content: Raw content string
            parsed_content: Parsed content dict (if available)

        Returns:
            ValidationResult with combined results from all validators
        """
        validators = self._content_validators.get(block_type, [])
        if not validators:
            return ValidationResult.success()

        for validator in validators:
            result = validator(raw_content, parsed_content)
            if not result.passed:
                self.logger.debug(
                    "content_validation_failed",
                    block_type=block_type,
                    validator_name=validator.__name__,
                    error=result.error,
                )
                return result

        return ValidationResult.success()
