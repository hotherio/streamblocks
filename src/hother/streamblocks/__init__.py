"""StreamBlocks - Real-time extraction and processing of structured blocks from text streams."""

__version__ = "0.1.0"

from hother.streamblocks.core.models import Block, BlockCandidate, ExtractedBlock
from hother.streamblocks.core.parsing import ParseStrategy, parse_as_json, parse_as_yaml
from hother.streamblocks.core.processor import StreamBlockProcessor
from hother.streamblocks.core.registry import Registry
from hother.streamblocks.core.types import (
    BaseContent,
    BaseMetadata,
    BlockDeltaEvent,
    BlockExtractedEvent,
    BlockRejectedEvent,
    BlockState,
    DetectionResult,
    EventType,
    ParseResult,
    RawTextEvent,
    StreamEvent,
)
from hother.streamblocks.syntaxes import (
    DelimiterFrontmatterSyntax,
    DelimiterPreambleSyntax,
    MarkdownFrontmatterSyntax,
)

# Rebuild event models to resolve forward references to ExtractedBlock
RawTextEvent.model_rebuild()
BlockDeltaEvent.model_rebuild()
BlockExtractedEvent.model_rebuild()
BlockRejectedEvent.model_rebuild()

__all__ = [
    # Core models
    "BaseContent",
    "BaseMetadata",
    "Block",
    "BlockCandidate",
    "BlockDeltaEvent",
    "BlockExtractedEvent",
    "BlockRejectedEvent",
    # Core types
    "BlockState",
    # Built-in syntaxes
    "DelimiterFrontmatterSyntax",
    "DelimiterPreambleSyntax",
    "DetectionResult",
    "EventType",
    "ExtractedBlock",
    "MarkdownFrontmatterSyntax",
    "ParseResult",
    # Parsing
    "ParseStrategy",
    "RawTextEvent",
    # Core components
    "Registry",
    "StreamBlockProcessor",
    # Events
    "StreamEvent",
    # Parsing utilities
    "parse_as_json",
    "parse_as_yaml",
]
