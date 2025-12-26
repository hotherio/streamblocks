"""Core types and enums for StreamBlocks."""

from __future__ import annotations

import time
from enum import StrEnum
from typing import TYPE_CHECKING, Annotated, Any, Literal, Self
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

if TYPE_CHECKING:
    from hother.streamblocks.core.models import ExtractedBlock


# ============== Content/Metadata Base Models ==============


class BaseMetadata(BaseModel):
    """Base metadata model with standard fields.

    All custom metadata models should inherit from this class and add
    their domain-specific fields.

    Example:
        >>> # Define custom metadata for a patch block
        >>> class PatchMetadata(BaseMetadata):
        ...     file_path: str
        ...     operation: Literal["create", "update", "delete"]
        ...
        >>> # Create instance with required base fields
        >>> metadata = PatchMetadata(
        ...     id="patch_001",
        ...     block_type="patch",
        ...     file_path="src/main.py",
        ...     operation="update"
        ... )
        >>> metadata.id
        'patch_001'
        >>> metadata.file_path
        'src/main.py'
    """

    id: str = Field(..., description="Block identifier")
    block_type: str = Field(..., description="Type of the block")


class BaseContent(BaseModel):
    """Base content model with raw content field.

    All custom content models should inherit from this class and optionally
    override the parse() method to add custom parsing logic. The raw_content
    field always preserves the original unparsed text.

    Example:
        >>> # Simple content model that just stores raw text
        >>> class SimpleContent(BaseContent):
        ...     pass
        ...
        >>> content = SimpleContent.parse("Hello, world!")
        >>> content.raw_content
        'Hello, world!'
        >>>
        >>> # Content model with custom parsing
        >>> class ItemsContent(BaseContent):
        ...     items: list[str] = []
        ...
        ...     @classmethod
        ...     def parse(cls, raw_text: str) -> Self:
        ...         items = [line.strip() for line in raw_text.split("\\n") if line.strip()]
        ...         return cls(raw_content=raw_text, items=items)
        ...
        >>> content = ItemsContent.parse("apple\\nbanana\\norange")
        >>> content.items
        ['apple', 'banana', 'orange']
        >>> content.raw_content  # Original text preserved
        'apple\\nbanana\\norange'
    """

    raw_content: str = Field(..., description="Raw unparsed content from the block")

    @classmethod
    def parse(cls, raw_text: str) -> Self:
        """Default parse method that just stores raw content.

        Override this in subclasses to add custom parsing logic.
        """
        return cls(raw_content=raw_text)


# ============== Event Types ==============


class EventType(StrEnum):
    """Event types emitted during stream processing."""

    # Lifecycle events
    STREAM_STARTED = "STREAM_STARTED"
    STREAM_FINISHED = "STREAM_FINISHED"
    STREAM_ERROR = "STREAM_ERROR"

    # Text events
    TEXT_CONTENT = "TEXT_CONTENT"
    TEXT_DELTA = "TEXT_DELTA"

    # Block lifecycle events
    BLOCK_START = "BLOCK_START"
    BLOCK_HEADER_DELTA = "BLOCK_HEADER_DELTA"
    BLOCK_METADATA_DELTA = "BLOCK_METADATA_DELTA"
    BLOCK_CONTENT_DELTA = "BLOCK_CONTENT_DELTA"
    BLOCK_METADATA_END = "BLOCK_METADATA_END"
    BLOCK_CONTENT_END = "BLOCK_CONTENT_END"
    BLOCK_END = "BLOCK_END"
    BLOCK_ERROR = "BLOCK_ERROR"

    # Custom events
    CUSTOM = "CUSTOM"


class BlockState(StrEnum):
    """Internal state of block detection."""

    SEARCHING = "searching"
    HEADER_DETECTED = "header_detected"
    ACCUMULATING_METADATA = "accumulating_metadata"
    ACCUMULATING_CONTENT = "accumulating_content"
    CLOSING_DETECTED = "closing_detected"
    REJECTED = "rejected"
    COMPLETED = "completed"


class BlockErrorCode(StrEnum):
    """Standard error codes for BlockErrorEvent.

    These codes categorize why a block extraction failed, enabling
    appropriate error handling and recovery strategies.

    Values:
        VALIDATION_FAILED: Block failed validator function checks (syntax or registry validation).
            Indicates the block structure is valid but business rules were violated.
        SIZE_EXCEEDED: Block exceeded max_block_size limit.
            Prevents memory exhaustion from maliciously large blocks.
        UNCLOSED_BLOCK: Block opened but never closed (stream ended).
            Indicates incomplete block at end of stream.
        UNKNOWN_TYPE: block_type not registered in registry.
            The syntax extracted a type that hasn't been registered.
        PARSE_FAILED: Block parsing failed (malformed YAML, invalid structure).
            The syntax couldn't parse the block content into metadata/content.
        MISSING_METADATA: Required metadata section missing.
            Parse succeeded but returned None for metadata.
        MISSING_CONTENT: Required content section missing.
            Parse succeeded but returned None for content.
        SYNTAX_ERROR: Syntax-specific error (custom validation).
            Used for syntax-specific validation failures.

    Example:
        >>> # Handle different error codes appropriately
        >>> async for event in processor.process_stream(stream):
        ...     if isinstance(event, BlockErrorEvent):
        ...         if event.error_code == BlockErrorCode.SIZE_EXCEEDED:
        ...             logger.warning(f"Block too large: {event.reason}")
        ...         elif event.error_code == BlockErrorCode.VALIDATION_FAILED:
        ...             logger.error(f"Validation failed: {event.reason}")
        ...         elif event.error_code == BlockErrorCode.UNCLOSED_BLOCK:
        ...             logger.info(f"Incomplete block at stream end: {event.reason}")
    """

    VALIDATION_FAILED = "VALIDATION_FAILED"
    SIZE_EXCEEDED = "SIZE_EXCEEDED"
    UNCLOSED_BLOCK = "UNCLOSED_BLOCK"
    UNKNOWN_TYPE = "UNKNOWN_TYPE"
    PARSE_FAILED = "PARSE_FAILED"
    MISSING_METADATA = "MISSING_METADATA"
    MISSING_CONTENT = "MISSING_CONTENT"
    SYNTAX_ERROR = "SYNTAX_ERROR"


class SectionType(StrEnum):
    """Block section types during accumulation.

    These represent the different phases of block parsing as content
    is accumulated line by line.
    """

    HEADER = "header"  # Block opening line(s) with inline metadata
    METADATA = "metadata"  # Dedicated metadata section (e.g., YAML frontmatter)
    CONTENT = "content"  # Main block content


# ============== Base Event ==============


class BaseEvent(BaseModel):
    """Base class for all StreamBlocks events.

    Attributes:
        type: Event type discriminator (defined in subclasses)
        timestamp: Unix timestamp in milliseconds (auto-generated)
        event_id: Unique event identifier (auto-generated)
        raw_event: Original provider event (preserved by adapters)
    """

    model_config = ConfigDict(frozen=True)

    timestamp: int = Field(default_factory=lambda: int(time.time() * 1000))
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    raw_event: Any | None = None


# ============== Lifecycle Events ==============


class StreamStartedEvent(BaseEvent):
    """Emitted when stream processing begins."""

    type: Literal[EventType.STREAM_STARTED] = EventType.STREAM_STARTED
    stream_id: str
    registry_name: str | None = None


class StreamFinishedEvent(BaseEvent):
    """Emitted when stream processing completes successfully."""

    type: Literal[EventType.STREAM_FINISHED] = EventType.STREAM_FINISHED
    stream_id: str
    blocks_extracted: int = 0
    blocks_rejected: int = 0
    total_events: int = 0
    duration_ms: int | None = None


class StreamErrorEvent(BaseEvent):
    """Emitted when stream processing fails."""

    type: Literal[EventType.STREAM_ERROR] = EventType.STREAM_ERROR
    stream_id: str
    error: str
    error_code: str | None = None


# ============== Text Events ==============


class TextContentEvent(BaseEvent):
    """Complete line of text outside any block."""

    type: Literal[EventType.TEXT_CONTENT] = EventType.TEXT_CONTENT
    content: str
    line_number: int


class TextDeltaEvent(BaseEvent):
    """Real-time text chunk (character/token level).

    Emitted immediately when text is received from stream, before line
    completion. Enables live streaming UIs and real-time text display.
    """

    type: Literal[EventType.TEXT_DELTA] = EventType.TEXT_DELTA
    delta: str
    inside_block: bool = False
    block_id: str | None = None
    section: str | None = None  # "header", "metadata", "content"


# ============== Block Events ==============


class BlockStartEvent(BaseEvent):
    """Block opening detected - begins block lifecycle.

    Emitted when a block opening marker is detected, before content
    accumulation. Useful for UIs to prepare display elements.
    """

    type: Literal[EventType.BLOCK_START] = EventType.BLOCK_START
    block_id: str
    block_type: str | None = None  # May not be known until parsed
    syntax: str
    start_line: int
    inline_metadata: dict[str, Any] | None = None


# ============== Section-Specific Delta Events ==============


class _BlockDeltaBase(BaseEvent):
    """Base class for section-specific block delta events.

    Internal base class - not exported. Use the concrete section events.
    """

    block_id: str
    delta: str
    syntax: str
    current_line: int
    accumulated_size: int


class BlockHeaderDeltaEvent(_BlockDeltaBase):
    """Delta event for block header section.

    Emitted when content is added to the header section of a block.
    May include inline metadata parsed from the header.
    """

    type: Literal[EventType.BLOCK_HEADER_DELTA] = EventType.BLOCK_HEADER_DELTA
    inline_metadata: dict[str, Any] | None = None


class BlockMetadataDeltaEvent(_BlockDeltaBase):
    """Delta event for block metadata section.

    Emitted when content is added to the metadata section of a block.
    The is_boundary flag indicates if this delta contains a section boundary marker.
    """

    type: Literal[EventType.BLOCK_METADATA_DELTA] = EventType.BLOCK_METADATA_DELTA
    is_boundary: bool = False


class BlockContentDeltaEvent(_BlockDeltaBase):
    """Delta event for block content section.

    Emitted when content is added to the content section of a block.
    This is the main body content after any metadata.
    """

    type: Literal[EventType.BLOCK_CONTENT_DELTA] = EventType.BLOCK_CONTENT_DELTA


# ============== Section End Events ==============


class BlockMetadataEndEvent(BaseEvent):
    """Emitted when metadata section completes (before content begins).

    This event signals that all metadata has been received and parsed.
    Enables early validation and processing before content accumulation.
    """

    type: Literal[EventType.BLOCK_METADATA_END] = EventType.BLOCK_METADATA_END
    block_id: str
    syntax: str
    start_line: int
    end_line: int
    raw_metadata: str
    parsed_metadata: dict[str, Any] | None = None
    validation_passed: bool = True
    validation_error: str | None = None


class BlockContentEndEvent(BaseEvent):
    """Emitted when content section completes (before BlockEndEvent).

    This event signals that all content has been received and parsed.
    Enables early validation and processing before final block extraction.
    """

    type: Literal[EventType.BLOCK_CONTENT_END] = EventType.BLOCK_CONTENT_END
    block_id: str
    syntax: str
    start_line: int
    end_line: int
    raw_content: str
    parsed_content: dict[str, Any] | None = None
    validation_passed: bool = True
    validation_error: str | None = None


class BlockEndEvent(BaseEvent):
    """Block successfully extracted and validated.

    Emitted when a block is fully parsed, validated, and ready for use.
    Contains the complete extracted content.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    type: Literal[EventType.BLOCK_END] = EventType.BLOCK_END
    block_id: str
    block_type: str
    syntax: str
    start_line: int
    end_line: int

    # Extracted content as dicts for serialization
    metadata: dict[str, Any]
    content: dict[str, Any]
    raw_content: str

    # Hash for deduplication/caching
    hash_id: str

    # Typed block reference (not serialized)
    _block: ExtractedBlock[Any, Any] | None = PrivateAttr(default=None)

    def get_block(self) -> ExtractedBlock[Any, Any] | None:
        """Get the typed ExtractedBlock if available."""
        return self._block


class BlockErrorEvent(BaseEvent):
    """Block extraction failed.

    Emitted when a block cannot be extracted due to validation failure,
    size limits, missing closing marker, or other errors.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    type: Literal[EventType.BLOCK_ERROR] = EventType.BLOCK_ERROR
    block_id: str | None = None
    reason: str
    error_code: BlockErrorCode | None = None
    syntax: str
    start_line: int
    end_line: int | None = None
    exception: Exception | None = Field(default=None, exclude=True)


# ============== Custom Events ==============


class CustomEvent(BaseEvent):
    """Application-specific custom events."""

    type: Literal[EventType.CUSTOM] = EventType.CUSTOM
    name: str
    value: dict[str, Any] = Field(default_factory=dict)


# ============== Event Union ==============


Event = Annotated[
    StreamStartedEvent
    | StreamFinishedEvent
    | StreamErrorEvent
    | TextContentEvent
    | TextDeltaEvent
    | BlockStartEvent
    | BlockHeaderDeltaEvent
    | BlockMetadataDeltaEvent
    | BlockContentDeltaEvent
    | BlockMetadataEndEvent
    | BlockContentEndEvent
    | BlockEndEvent
    | BlockErrorEvent
    | CustomEvent,
    Field(discriminator="type"),
]


# ============== Detection/Parse Results ==============


class DetectionResult(BaseModel):
    """Result from syntax detection attempt."""

    is_opening: bool = False
    is_closing: bool = False
    is_metadata_boundary: bool = False
    metadata: dict[str, Any] | None = None


class ParseResult[TMetadata: BaseMetadata, TContent: BaseContent](BaseModel):
    """Result from parsing attempt."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    success: bool
    metadata: TMetadata | None = None
    content: TContent | None = None
    error: str | None = None
    exception: Exception | None = None
