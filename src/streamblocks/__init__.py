"""StreamBlocks - Real-time extraction and processing of structured blocks from text streams."""

__version__ = "0.1.0"

from streamblocks.core.models import BaseContent, BaseMetadata, Block, BlockCandidate
from streamblocks.core.processor import StreamBlockProcessor
from streamblocks.core.registry import BlockRegistry
from streamblocks.core.types import (
    BlockState,
    DetectionResult,
    EventType,
    ParseResult,
    StreamEvent,
)
from streamblocks.syntaxes import (
    DelimiterFrontmatterSyntax,
    DelimiterPreambleSyntax,
    MarkdownFrontmatterSyntax,
)

__all__ = [
    # Core types
    "EventType",
    "BlockState",
    "StreamEvent",
    "DetectionResult",
    "ParseResult",
    # Core models
    "BaseMetadata",
    "BaseContent",
    "Block",
    "BlockCandidate",
    # Core components
    "BlockRegistry",
    "StreamBlockProcessor",
    # Built-in syntaxes
    "DelimiterPreambleSyntax",
    "MarkdownFrontmatterSyntax",
    "DelimiterFrontmatterSyntax",
]
