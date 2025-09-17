"""Core types and protocols for StreamBlocks."""

from .types import (
    BlockState,
    BlockSyntax,
    DetectionResult,
    EventType,
    ParseResult,
    StreamEvent,
)

__all__ = [
    "EventType",
    "BlockState",
    "StreamEvent",
    "DetectionResult",
    "ParseResult",
    "BlockSyntax",
]
