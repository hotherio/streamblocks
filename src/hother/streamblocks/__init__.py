"""StreamBlocks - Real-time extraction and processing of structured blocks from text streams."""

__version__ = "0.1.0"

from hother.streamblocks.core.models import BaseContent, BaseMetadata, Block, BlockCandidate, BlockDefinition
from hother.streamblocks.core.processor import StreamBlockProcessor
from hother.streamblocks.core.registry import Registry
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
    # Core models
    "BaseContent",
    "BaseMetadata",
    "Block",
    "BlockCandidate",
    "BlockDefinition",
    # Core types
    "BlockState",
    # Built-in syntaxes
    "DelimiterFrontmatterSyntax",
    "DelimiterPreambleSyntax",
    "DetectionResult",
    "EventType",
    "MarkdownFrontmatterSyntax",
    "ParseResult",
    # Core components
    "Registry",
    "StreamBlockProcessor",
    "StreamEvent",
]
