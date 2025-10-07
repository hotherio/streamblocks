"""Core types and enums for StreamBlocks."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, TypeVar

from pydantic import BaseModel

if TYPE_CHECKING:
    from hother.streamblocks.core.models import Block

# Core type variables
TMetadata = TypeVar("TMetadata", bound=BaseModel)
TContent = TypeVar("TContent", bound=BaseModel)
TBlockDef = TypeVar("TBlockDef", bound=BaseModel)


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


class StreamEvent[TMetadata: BaseModel, TContent: BaseModel](BaseModel):
    """Base event emitted during stream processing."""

    type: EventType
    data: str  # Raw text (line or complete block)
    block: Block[TMetadata, TContent] | None = None  # For BLOCK_EXTRACTED events
    content: dict[str, object] | None = None  # For other event-specific data


@dataclass
class DetectionResult:
    """Result from syntax detection attempt."""

    is_opening: bool = False
    is_closing: bool = False
    is_metadata_boundary: bool = False
    metadata: dict[str, object] | None = None  # For inline metadata (e.g., preamble syntax)


@dataclass
class ParseResult[TMetadata: BaseModel, TContent: BaseModel]:
    """Result from parsing attempt."""

    success: bool
    metadata: TMetadata | None = None
    content: TContent | None = None
    error: str | None = None
