"""Core types and enums for StreamBlocks."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Generic, TypeVar

from pydantic import BaseModel

# Core type variables
TMetadata = TypeVar("TMetadata", bound=BaseModel)
TContent = TypeVar("TContent", bound=BaseModel)


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
    """Base event emitted during stream processing."""

    type: EventType
    data: str  # Raw bytes/text
    metadata: dict[str, object] | None = None


@dataclass
class DetectionResult:
    """Result from syntax detection attempt."""

    is_opening: bool = False
    is_closing: bool = False
    is_metadata_boundary: bool = False
    metadata: dict[str, object] | None = None  # For inline metadata (e.g., preamble syntax)


@dataclass
class ParseResult(Generic[TMetadata, TContent]):
    """Result from parsing attempt."""

    success: bool
    metadata: TMetadata | None = None
    content: TContent | None = None
    error: str | None = None
