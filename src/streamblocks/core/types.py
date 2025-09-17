"""Core type definitions for StreamBlocks.

This module defines the foundational types and protocols used throughout
the StreamBlocks library. These include:

- Event types and states for stream processing
- Data models for detection and parsing results
- The BlockSyntax protocol for implementing custom syntaxes

All types are designed to be type-safe and work with Python 3.13+.
"""

from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Generic, Protocol, TypeVar

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from .models import BlockCandidate


# Type variables for generic metadata and content
# These allow BlockSyntax implementations to specify their own
# strongly-typed metadata and content models
TMetadata = TypeVar("TMetadata", bound=BaseModel)
"""Type variable for block metadata - must be a Pydantic BaseModel."""

TContent = TypeVar("TContent", bound=BaseModel)
"""Type variable for block content - must be a Pydantic BaseModel."""


class EventType(StrEnum):
    """Event types emitted during stream processing."""

    RAW_TEXT = "raw_text"
    BLOCK_DELTA = "block_delta"
    BLOCK_EXTRACTED = "block_extracted"
    BLOCK_REJECTED = "block_rejected"


class BlockState(StrEnum):
    """Internal state of block detection."""

    SEARCHING = "searching"
    HEADER_DETECTED = "header_detected"
    ACCUMULATING_METADATA = "accumulating_metadata"
    ACCUMULATING_CONTENT = "accumulating_content"
    CLOSING_DETECTED = "closing_detected"
    REJECTED = "rejected"
    COMPLETED = "completed"


class StreamEvent(BaseModel, Generic[TMetadata, TContent]):
    """Base event emitted during stream processing.

    All events have a type and raw data. Additional metadata
    depends on the event type.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    type: EventType
    data: str  # Raw bytes/text
    metadata: dict[str, Any] | None = None


@dataclass
class DetectionResult:
    """Result from syntax detection attempt.

    Used by syntax implementations to communicate what was
    detected on a given line.
    """

    is_opening: bool = False
    is_closing: bool = False
    is_metadata_boundary: bool = False
    metadata: dict[str, Any] | None = None  # For inline metadata (e.g., preamble syntax)


@dataclass
class ParseResult(Generic[TMetadata, TContent]):
    """Result from parsing attempt.

    Contains either successfully parsed metadata/content or
    an error message explaining the failure.
    """

    success: bool
    metadata: TMetadata | None = None
    content: TContent | None = None
    error: str | None = None


class BlockSyntax(Protocol[TMetadata, TContent]):
    """Protocol for defining block syntax parsers.

    Each syntax implementation must provide methods for:
    - Line detection (opening/closing/boundaries)
    - Metadata accumulation logic
    - Block parsing
    - Optional validation

    The protocol is generic over metadata and content types,
    allowing type-safe parsing of different block formats.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique syntax identifier."""
        ...

    @abstractmethod
    def detect_line(self, line: str, context: BlockCandidate | None = None) -> DetectionResult:
        """Detect if line is significant for this syntax.

        Args:
            line: Current line to check
            context: Current candidate if we're inside a block, None if searching

        Returns:
            DetectionResult indicating what was detected
        """
        ...

    @abstractmethod
    def should_accumulate_metadata(self, candidate: BlockCandidate) -> bool:
        """Check if syntax expects more metadata lines.

        Some syntaxes have inline metadata (e.g., preamble), while
        others have separate metadata sections (e.g., frontmatter).
        """
        ...

    @abstractmethod
    def parse_block(self, candidate: BlockCandidate) -> ParseResult[TMetadata, TContent]:
        """Parse a complete block candidate.

        Called when a closing marker is detected. Should parse
        the accumulated lines into typed metadata and content.
        """
        ...

    def validate_block(self, metadata: TMetadata, content: TContent) -> bool:
        """Additional validation after parsing.

        Optional method for extra validation beyond Pydantic models.
        Default implementation accepts all parsed blocks.
        """
        return True

    # Optional performance optimization methods

    def get_opening_pattern(self) -> str | None:
        """Get regex pattern for quickly matching opening markers.

        Returns None if no optimization is possible.
        This allows stream processors to pre-filter lines.
        """
        return None

    def get_closing_pattern(self) -> str | None:
        """Get regex pattern for quickly matching closing markers.

        Returns None if no optimization is possible.
        This helps quickly identify block boundaries.
        """
        return None

    def supports_nested_blocks(self) -> bool:
        """Check if this syntax supports nested blocks.

        Default is False. Override to enable nested block support.
        """
        return False

    def get_block_type_hints(self) -> list[str]:
        """Get list of block types this syntax typically produces.

        Used for registry optimization and documentation.
        """
        return []
