"""Core types and protocols for StreamBlocks."""

from .models import Block, BlockCandidate
from .registry import BlockRegistry
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
    "BlockCandidate",
    "Block",
    "BlockRegistry",
]
