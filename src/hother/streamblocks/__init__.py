"""StreamBlocks - Real-time extraction and processing of structured blocks from text streams."""

__version__ = "0.1.0"

from hother.streamblocks.adapters import (
    AdapterDetector,
    AnthropicAdapter,
    AttributeAdapter,
    CallableAdapter,
    GeminiAdapter,
    IdentityAdapter,
    OpenAIAdapter,
    StreamAdapter,
)
from hother.streamblocks.core.models import Block, BlockCandidate, ExtractedBlock
from hother.streamblocks.core.parsing import ParseStrategy, parse_as_json, parse_as_yaml
from hother.streamblocks.core.processor import StreamBlockProcessor, StreamState
from hother.streamblocks.core.registry import MetadataValidationFailureMode, Registry, ValidationResult
from hother.streamblocks.core.types import (
    BaseContent,
    BaseEvent,
    BaseMetadata,
    BlockContentDeltaEvent,
    BlockContentEndEvent,
    BlockDeltaEvent,
    BlockEndEvent,
    BlockErrorCode,
    BlockErrorEvent,
    BlockHeaderDeltaEvent,
    BlockMetadataDeltaEvent,
    BlockMetadataEndEvent,
    BlockStartEvent,
    BlockState,
    CustomEvent,
    DetectionResult,
    Event,
    EventType,
    ParseResult,
    StreamErrorEvent,
    StreamFinishedEvent,
    StreamStartedEvent,
    TextContentEvent,
    TextDeltaEvent,
)
from hother.streamblocks.syntaxes import (
    DelimiterFrontmatterSyntax,
    DelimiterPreambleSyntax,
    MarkdownFrontmatterSyntax,
)

# Rebuild event models to resolve forward references to ExtractedBlock
BlockEndEvent.model_rebuild()

__all__ = [
    # Adapters
    "AdapterDetector",
    "AnthropicAdapter",
    "AttributeAdapter",
    # Core models
    "BaseContent",
    "BaseEvent",
    "BaseMetadata",
    "Block",
    "BlockCandidate",
    # Events
    "BlockContentDeltaEvent",
    "BlockContentEndEvent",
    "BlockDeltaEvent",
    "BlockEndEvent",
    "BlockErrorCode",
    "BlockErrorEvent",
    "BlockHeaderDeltaEvent",
    "BlockMetadataDeltaEvent",
    "BlockMetadataEndEvent",
    "BlockStartEvent",
    "BlockState",
    "CallableAdapter",
    "CustomEvent",
    # Built-in syntaxes
    "DelimiterFrontmatterSyntax",
    "DelimiterPreambleSyntax",
    # Core types
    "DetectionResult",
    "Event",
    "EventType",
    "ExtractedBlock",
    "GeminiAdapter",
    "IdentityAdapter",
    "MarkdownFrontmatterSyntax",
    # Validation
    "MetadataValidationFailureMode",
    "OpenAIAdapter",
    "ParseResult",
    # Parsing
    "ParseStrategy",
    # Core components
    "Registry",
    "StreamAdapter",
    "StreamBlockProcessor",
    "StreamErrorEvent",
    "StreamFinishedEvent",
    "StreamStartedEvent",
    "StreamState",
    "TextContentEvent",
    "TextDeltaEvent",
    "ValidationResult",
    "parse_as_json",
    "parse_as_yaml",
]
