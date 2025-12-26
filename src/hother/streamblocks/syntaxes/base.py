"""Base syntax class and utilities for StreamBlocks syntax implementations."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

import yaml
from pydantic import ValidationError

# Import BaseMetadata at module level for runtime isinstance checks
from hother.streamblocks.core.types import BaseMetadata, ParseResult

if TYPE_CHECKING:
    from hother.streamblocks.core.models import BlockCandidate, ExtractedBlock
    from hother.streamblocks.core.types import BaseContent, DetectionResult

# Module-level logger for debugging YAML parsing failures
_logger = logging.getLogger(__name__)


class YAMLFrontmatterMixin:
    """Mixin providing YAML frontmatter parsing utilities.

    This mixin reduces code duplication in syntaxes that use YAML for metadata.
    It provides two parsing methods:
    - _parse_yaml_metadata: Silent failure, returns None on error
    - _parse_yaml_metadata_strict: Returns exception for error handling

    Example:
        >>> class MySyntax(BaseSyntax, YAMLFrontmatterMixin):
        ...     def extract_block_type(self, candidate):
        ...         metadata = self._parse_yaml_metadata(candidate.metadata_lines)
        ...         return metadata.get("block_type") if metadata else None
    """

    def _parse_yaml_metadata(self, metadata_lines: list[str]) -> dict[str, Any] | None:
        """Parse YAML from metadata lines. Returns None on error.

        Args:
            metadata_lines: Lines containing YAML content

        Returns:
            Parsed YAML as dict, or None if parsing fails or lines are empty
        """
        if not metadata_lines:
            return None
        yaml_content = "\n".join(metadata_lines)
        try:
            return yaml.safe_load(yaml_content) or {}
        except yaml.YAMLError as e:
            # Log parse failure for debugging
            _logger.debug(
                "YAML parse failed: %s (lines=%d, preview=%s)",
                str(e),
                len(metadata_lines),
                yaml_content[:100] if yaml_content else "",
            )
            return None

    def _parse_yaml_metadata_strict(self, metadata_lines: list[str]) -> tuple[dict[str, Any], Exception | None]:
        """Parse YAML, returning both result and exception.

        Use this method when you need to report the error in a ParseResult.

        Args:
            metadata_lines: Lines containing YAML content

        Returns:
            Tuple of (parsed dict, exception or None)
        """
        if not metadata_lines:
            return {}, None
        yaml_content = "\n".join(metadata_lines)
        try:
            return yaml.safe_load(yaml_content) or {}, None
        except yaml.YAMLError as e:
            return {}, e


class BaseSyntax(ABC):
    """Abstract base class for syntax implementations.

    This class provides default implementations and helper methods to reduce
    code duplication across syntax implementations. It implements the BlockSyntax
    protocol and provides a template method pattern for parsing blocks.

    Custom syntax implementations should:
    1. Inherit from this class
    2. Implement the abstract methods marked with @abstractmethod
    3. Optionally override validate_block() for custom validation

    Example:
        >>> class MySyntax(BaseSyntax):
        ...     def detect_line(self, line: str, candidate: BlockCandidate | None) -> DetectionResult:
        ...         # Implementation here
        ...         pass
        ...
        ...     def should_accumulate_metadata(self, candidate: BlockCandidate) -> bool:
        ...         # Implementation here
        ...         pass
        ...
        ...     def extract_block_type(self, candidate: BlockCandidate) -> str | None:
        ...         # Implementation here
        ...         pass
        ...
        ...     def parse_block(self, candidate: BlockCandidate, block_class: type[Any] | None = None) -> ParseResult[BaseMetadata, BaseContent]:
        ...         # Implementation here
        ...         pass
    """

    # Abstract methods that must be implemented by subclasses

    @abstractmethod
    def detect_line(self, line: str, candidate: BlockCandidate | None) -> DetectionResult:
        """Detect if line is significant for this syntax.

        This method is called for each line in the stream to determine if it's
        an opening marker, closing marker, metadata boundary, or regular content.

        Args:
            line: Current line to check
            candidate: Current candidate if we're inside a block, None if searching

        Returns:
            DetectionResult indicating what was detected
        """
        ...

    @abstractmethod
    def should_accumulate_metadata(self, candidate: BlockCandidate) -> bool:
        """Check if syntax expects more metadata lines.

        This method determines whether the processor should continue accumulating
        metadata lines or move to content accumulation.

        Args:
            candidate: The current block candidate

        Returns:
            True if more metadata lines are expected, False otherwise
        """
        ...

    @abstractmethod
    def extract_block_type(self, candidate: BlockCandidate) -> str | None:
        """Extract block_type from candidate without full parsing.

        This method performs minimal parsing to extract just the block_type,
        which is needed to look up the appropriate block_class from the registry.

        Args:
            candidate: The block candidate to extract block_type from

        Returns:
            The block_type string, or None if it cannot be determined
        """
        ...

    @abstractmethod
    def parse_block(
        self, candidate: BlockCandidate, block_class: type[Any] | None = None
    ) -> ParseResult[BaseMetadata, BaseContent]:
        """Parse a complete block candidate using the specified block class.

        Args:
            candidate: The complete block candidate to parse
            block_class: The Block class to use for parsing (inherits from Block[M, C])
                        If None, uses default base classes

        Returns:
            ParseResult with parsed metadata and content or error
        """
        ...

    # Helper methods for metadata and validation

    def _safe_parse_metadata(
        self,
        metadata_class: type[BaseMetadata],
        data: dict[str, Any],
    ) -> BaseMetadata | ParseResult[BaseMetadata, BaseContent]:
        """Safely parse metadata dict into Pydantic model.

        Helper method to reduce code duplication across syntax implementations.
        Handles ValidationError and returns either the parsed metadata or a
        ParseResult with error information.

        Args:
            metadata_class: The metadata class to instantiate
            data: Dictionary of metadata fields

        Returns:
            Parsed metadata instance, or ParseResult with error on failure
        """
        try:
            return metadata_class(**data)
        except ValidationError as e:
            return ParseResult(
                success=False,
                error=f"Metadata validation error: {e}",
                exception=e,
            )
        except (TypeError, ValueError, KeyError) as e:
            return ParseResult(
                success=False,
                error=f"Invalid metadata: {e}",
                exception=e,
            )

    def _safe_parse_content(
        self,
        content_class: type[BaseContent],
        raw_text: str,
    ) -> BaseContent | ParseResult[BaseMetadata, BaseContent]:
        """Safely parse content into Pydantic model.

        Helper method to reduce code duplication across syntax implementations.
        Handles ValidationError and returns either the parsed content or a
        ParseResult with error information.

        Args:
            content_class: The content class to instantiate
            raw_text: Raw text content to parse

        Returns:
            Parsed content instance, or ParseResult with error on failure
        """
        try:
            return content_class.parse(raw_text)
        except ValidationError as e:
            return ParseResult(
                success=False,
                error=f"Content validation error: {e}",
                exception=e,
            )
        except (TypeError, ValueError, KeyError) as e:
            return ParseResult(
                success=False,
                error=f"Invalid content: {e}",
                exception=e,
            )

    # Default implementations

    def validate_block(self, _block: ExtractedBlock[BaseMetadata, BaseContent]) -> bool:
        """Additional validation after parsing.

        Default implementation always returns True. Override this method
        to add custom validation logic specific to your syntax or block type.

        Args:
            _block: Extracted block to validate

        Returns:
            True if the block is valid, False otherwise
        """
        return True

    def parse_metadata_early(self, candidate: BlockCandidate) -> dict[str, Any] | None:
        """Parse metadata section early, before content accumulation.

        This method is called when the metadata section completes, allowing
        early validation and processing. The result can be cached in the
        candidate for reuse during full block parsing.

        Default implementation returns None (no early parsing).
        Override in subclasses to provide early metadata parsing.

        Args:
            candidate: The current block candidate with metadata accumulated

        Returns:
            Parsed metadata dict if successful, None if parsing not supported
            or failed
        """
        return None

    def parse_content_early(self, candidate: BlockCandidate) -> dict[str, Any] | None:
        """Parse content section early, before final block extraction.

        This method is called when the content section completes (block closes),
        allowing early validation. The result can be cached in the candidate
        for reuse during full block parsing.

        Default implementation returns None (no early parsing).
        Override in subclasses to provide early content parsing.

        Args:
            candidate: The complete block candidate with content accumulated

        Returns:
            Parsed content dict if successful, None if parsing not supported
            or failed
        """
        return None
