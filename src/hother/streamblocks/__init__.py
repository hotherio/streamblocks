"""StreamBlocks - Real-time extraction and processing of structured blocks from text streams."""

__version__ = "0.1.0"

from hother.streamblocks.core.models import BaseContent, BaseMetadata, Block, BlockCandidate
from hother.streamblocks.core.processor import StreamBlockProcessor
from hother.streamblocks.core.registry import BlockRegistry, Registry
from hother.streamblocks.core.types import (
    BlockState,
    DetectionResult,
    EventType,
    ParseResult,
    StreamEvent,
)
from hother.streamblocks.syntaxes import (
    DelimiterFrontmatterSyntax,
    DelimiterPreambleSyntax,
    MarkdownFrontmatterSyntax,
)

__all__ = [
    "BaseContent",
    # Core models
    "BaseMetadata",
    "Block",
    "BlockCandidate",
    "BlockRegistry",  # Deprecated alias
    "BlockState",
    "DelimiterFrontmatterSyntax",
    # Built-in syntaxes
    "DelimiterPreambleSyntax",
    "DetectionResult",
    # Core types
    "EventType",
    "MarkdownFrontmatterSyntax",
    "ParseResult",
    # Core components
    "Registry",
    "StreamBlockProcessor",
    "StreamEvent",
]
