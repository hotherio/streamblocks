"""Base syntax class and utilities for StreamBlocks syntax implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from hother.streamblocks.core.models import BlockCandidate, ExtractedBlock
    from hother.streamblocks.core.types import BaseContent, BaseMetadata, DetectionResult, ParseResult


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
