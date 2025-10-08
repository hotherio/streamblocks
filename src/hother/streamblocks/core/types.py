"""Core types and enums for StreamBlocks."""

from __future__ import annotations

from enum import StrEnum, auto
from typing import TYPE_CHECKING, Annotated, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from hother.streamblocks.core.models import ExtractedBlock


class BaseMetadata(BaseModel):
    """Base metadata model with standard fields.

    All custom metadata models should inherit from this class.
    """

    id: str = Field(..., description="Block identifier")
    block_type: str = Field(..., description="Type of the block")


class BaseContent(BaseModel):
    """Base content model with raw content field.

    All custom content models should inherit from this class.
    The raw_content field always contains the unparsed block content.
    """

    raw_content: str = Field(..., description="Raw unparsed content from the block")

    @classmethod
    def parse(cls, raw_text: str) -> BaseContent:
        """Default parse method that just stores raw content.

        Override this in subclasses to add custom parsing logic.
        """
        return cls(raw_content=raw_text)


# Core type variables
TMetadata = TypeVar("TMetadata", bound=BaseMetadata)
TContent = TypeVar("TContent", bound=BaseContent)


class EventType(StrEnum):
    """Event types emitted during stream processing."""

    RAW_TEXT = auto()
    BLOCK_DELTA = auto()
    BLOCK_EXTRACTED = auto()
    BLOCK_REJECTED = auto()


class BlockState(StrEnum):
    """Internal state of block detection."""

    SEARCHING = "searching"
    HEADER_DETECTED = "header_detected"
    ACCUMULATING_METADATA = "accumulating_metadata"
    ACCUMULATING_CONTENT = "accumulating_content"
    CLOSING_DETECTED = "closing_detected"
    REJECTED = "rejected"
    COMPLETED = "completed"


class BaseStreamEvent[TMetadata: BaseMetadata, TContent: BaseContent](BaseModel):
    """Base class for all stream events."""

    data: str


class RawTextEvent[TMetadata: BaseMetadata, TContent: BaseContent](BaseStreamEvent[TMetadata, TContent]):
    """Event for raw text that's not part of a block."""

    type: Literal[EventType.RAW_TEXT] = EventType.RAW_TEXT
    line_number: int


class BlockDeltaEvent[TMetadata: BaseMetadata, TContent: BaseContent](BaseStreamEvent[TMetadata, TContent]):
    """Event for partial block updates."""

    type: Literal[EventType.BLOCK_DELTA] = EventType.BLOCK_DELTA
    syntax: str
    start_line: int
    current_line: int
    section: str
    delta: str
    accumulated: str


class BlockExtractedEvent[TMetadata: BaseMetadata, TContent: BaseContent](BaseStreamEvent[TMetadata, TContent]):
    """Event for successfully extracted blocks."""

    type: Literal[EventType.BLOCK_EXTRACTED] = EventType.BLOCK_EXTRACTED
    block: ExtractedBlock[TMetadata, TContent]


class BlockRejectedEvent[TMetadata: BaseMetadata, TContent: BaseContent](BaseStreamEvent[TMetadata, TContent]):
    """Event for rejected blocks."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    type: Literal[EventType.BLOCK_REJECTED] = EventType.BLOCK_REJECTED
    reason: str
    syntax: str
    start_line: int
    end_line: int
    exception: Exception | None = None


# Discriminated union type for all stream events
type StreamEvent[TMetadata: BaseMetadata, TContent: BaseContent] = Annotated[
    RawTextEvent[TMetadata, TContent]
    | BlockDeltaEvent[TMetadata, TContent]
    | BlockExtractedEvent[TMetadata, TContent]
    | BlockRejectedEvent[TMetadata, TContent],
    Field(discriminator="type"),
]


class DetectionResult(BaseModel):
    """Result from syntax detection attempt."""

    is_opening: bool = False
    is_closing: bool = False
    is_metadata_boundary: bool = False
    metadata: dict[str, object] | None = None  # For inline metadata (e.g., preamble syntax)


class ParseResult[TMetadata: BaseMetadata, TContent: BaseContent](BaseModel):
    """Result from parsing attempt."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    success: bool
    metadata: TMetadata | None = None
    content: TContent | None = None
    error: str | None = None
    exception: Exception | None = None
