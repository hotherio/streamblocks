"""Abstract base classes for common syntax patterns.

This module provides abstract base classes that implement common
functionality for different types of block syntaxes:

- BaseSyntax: Core functionality for all syntaxes
- FrontmatterSyntax: For YAML frontmatter-style blocks
- DelimiterSyntax: For delimiter-based blocks
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Generic

from streamblocks.core.types import (
    BlockState,
    DetectionResult,
    ParseResult,
    TContent,
    TMetadata,
)

if TYPE_CHECKING:
    from streamblocks.core.models import BlockCandidate


class BaseSyntax(ABC, Generic[TMetadata, TContent]):
    """Abstract base class for block syntax implementations.

    Provides common functionality and sensible defaults for syntax parsers.
    Subclasses should implement the abstract methods and can override
    the optional methods for customization.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique syntax identifier."""
        ...

    @abstractmethod
    def detect_line(self, line: str, context: BlockCandidate | None = None) -> DetectionResult:
        """Detect if line is significant for this syntax."""
        ...

    @abstractmethod
    def should_accumulate_metadata(self, candidate: BlockCandidate) -> bool:
        """Check if syntax expects more metadata lines."""
        ...

    @abstractmethod
    def parse_block(self, candidate: BlockCandidate) -> ParseResult[TMetadata, TContent]:
        """Parse a complete block candidate."""
        ...

    def validate_block(self, metadata: TMetadata, content: TContent) -> bool:
        """Additional validation after parsing.

        Default implementation accepts all parsed blocks.
        Override to add custom validation logic.
        """
        return True

    def get_opening_pattern(self) -> str | None:
        """Get regex pattern for opening markers."""
        return None

    def get_closing_pattern(self) -> str | None:
        """Get regex pattern for closing markers."""
        return None

    def supports_nested_blocks(self) -> bool:
        """Check if this syntax supports nested blocks."""
        return False

    def get_block_type_hints(self) -> list[str]:
        """Get list of block types this syntax typically produces."""
        return []

    # Helper methods for subclasses

    def _create_error_result(self, error: str) -> ParseResult[TMetadata, TContent]:
        """Create a failed parse result with error message."""
        return ParseResult[TMetadata, TContent](success=False, error=error)

    def _create_success_result(
        self, metadata: TMetadata, content: TContent
    ) -> ParseResult[TMetadata, TContent]:
        """Create a successful parse result."""
        return ParseResult[TMetadata, TContent](success=True, metadata=metadata, content=content)


class FrontmatterSyntax(BaseSyntax[TMetadata, TContent], ABC):
    """Abstract base for YAML frontmatter-style syntaxes.

    This base class handles blocks that have:
    - Opening delimiter (e.g., "---")
    - YAML metadata section
    - Closing delimiter (e.g., "---")
    - Content section

    Subclasses need to provide:
    - Metadata and content model classes
    - Custom delimiters if different from "---"
    - Any additional parsing logic
    """

    @property
    def opening_delimiter(self) -> str:
        """Opening delimiter for frontmatter section."""
        return "---"

    @property
    def closing_delimiter(self) -> str:
        """Closing delimiter for frontmatter section."""
        return "---"

    def detect_line(self, line: str, context: BlockCandidate | None = None) -> DetectionResult:
        """Detect frontmatter boundaries."""
        stripped = line.strip()

        # Not in a block - check for opening
        if context is None:
            if stripped == self.opening_delimiter:
                return DetectionResult(is_opening=True)
            return DetectionResult()

        # In a block - check state
        if context.state == BlockState.ACCUMULATING_METADATA:
            if stripped == self.closing_delimiter:
                return DetectionResult(is_metadata_boundary=True)
        elif context.state == BlockState.ACCUMULATING_CONTENT:
            # Frontmatter blocks typically don't have explicit end markers
            pass

        return DetectionResult()

    def should_accumulate_metadata(self, candidate: BlockCandidate) -> bool:
        """Frontmatter accumulates metadata until closing delimiter."""
        return candidate.state == BlockState.ACCUMULATING_METADATA

    def get_opening_pattern(self) -> str | None:
        """Pattern for opening delimiter."""
        return f"^{re.escape(self.opening_delimiter)}$"

    def get_closing_pattern(self) -> str | None:
        """Frontmatter doesn't have explicit closing pattern."""
        return None

    @abstractmethod
    def parse_metadata(self, yaml_text: str) -> TMetadata:
        """Parse YAML text into metadata model.

        Subclasses must implement this to create their specific metadata type.
        """
        ...

    @abstractmethod
    def parse_content(self, content_text: str) -> TContent:
        """Parse content text into content model.

        Subclasses must implement this to create their specific content type.
        """
        ...

    def parse_block(self, candidate: BlockCandidate) -> ParseResult[TMetadata, TContent]:
        """Parse frontmatter block into metadata and content."""
        try:
            # Join metadata lines (excluding delimiters)
            metadata_text = "\n".join(candidate.metadata_lines)
            content_text = "\n".join(candidate.content_lines)

            # Parse components
            metadata = self.parse_metadata(metadata_text)
            content = self.parse_content(content_text)

            # Validate if needed
            if not self.validate_block(metadata, content):
                return self._create_error_result("Block validation failed")

            return self._create_success_result(metadata, content)

        except Exception as e:
            return self._create_error_result(f"Parse error: {e}")


class DelimiterSyntax(BaseSyntax[TMetadata, TContent], ABC):
    """Abstract base for delimiter-based syntaxes.

    This base class handles blocks that have:
    - Opening delimiter with optional inline metadata
    - Content section
    - Closing delimiter

    Examples:
    - !!block123:type:params
    - ... content ...
    - !!block123:end

    Subclasses need to provide:
    - Delimiter patterns
    - Metadata extraction from opening line
    - Content parsing logic
    """

    @property
    @abstractmethod
    def delimiter_prefix(self) -> str:
        """Prefix for block delimiters (e.g., '!!')."""
        ...

    @property
    def end_suffix(self) -> str:
        """Suffix for end markers (e.g., ':end')."""
        return ":end"

    def detect_line(self, line: str, context: BlockCandidate | None = None) -> DetectionResult:
        """Detect delimiter-based markers."""
        stripped = line.strip()

        # Check for opening marker
        if context is None:
            if stripped.startswith(self.delimiter_prefix):
                # Extract any inline metadata
                metadata = self._extract_inline_metadata(stripped)
                return DetectionResult(is_opening=True, metadata=metadata)
            return DetectionResult()

        # Check for closing marker (must match hash)
        if context and context.state == BlockState.ACCUMULATING_CONTENT:
            # Get hash from opening metadata
            hash_id = getattr(context.syntax, "name", "unknown")  # This is simplified
            expected_closing = f"{self.delimiter_prefix}{hash_id}{self.end_suffix}"
            if stripped == expected_closing:
                return DetectionResult(is_closing=True)

        return DetectionResult()

    def should_accumulate_metadata(self, candidate: BlockCandidate) -> bool:
        """Delimiter syntaxes typically have inline metadata only."""
        return False

    def get_opening_pattern(self) -> str | None:
        """Pattern for opening delimiter."""
        return f"^{re.escape(self.delimiter_prefix)}"

    def get_closing_pattern(self) -> str | None:
        """Pattern for closing delimiter."""
        return f"^{re.escape(self.delimiter_prefix)}.*{re.escape(self.end_suffix)}$"

    @abstractmethod
    def _extract_inline_metadata(self, opening_line: str) -> dict[str, str]:
        """Extract metadata from opening delimiter line.

        Args:
            opening_line: The full opening line (e.g., "!!block123:type:params")

        Returns:
            Dictionary of extracted metadata
        """
        ...

    @abstractmethod
    def parse_metadata_dict(self, metadata_dict: dict[str, str]) -> TMetadata:
        """Convert metadata dictionary to typed metadata model."""
        ...

    @abstractmethod
    def parse_content(self, content_text: str) -> TContent:
        """Parse content text into content model."""
        ...

    def parse_block(self, candidate: BlockCandidate) -> ParseResult[TMetadata, TContent]:
        """Parse delimiter-based block into metadata and content."""
        try:
            # Extract metadata from the first line (opening delimiter)
            if not candidate.lines:
                return self._create_error_result("No lines in candidate")

            opening_line = candidate.lines[0]
            metadata_dict = self._extract_inline_metadata(opening_line)

            # Parse metadata
            metadata = self.parse_metadata_dict(metadata_dict)

            # Join content lines (excluding opening/closing delimiters)
            # Content is everything except first and last line
            content_lines = candidate.content_lines
            content_text = "\n".join(content_lines)

            # Parse content
            content = self.parse_content(content_text)

            # Validate if needed
            if not self.validate_block(metadata, content):
                return self._create_error_result("Block validation failed")

            return self._create_success_result(metadata, content)

        except Exception as e:
            return self._create_error_result(f"Parse error: {e}")
