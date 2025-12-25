"""StreamBlocks - Real-time extraction and processing of structured blocks from text streams."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("streamblocks")
except PackageNotFoundError:
    # Package not installed (e.g., running from source)
    __version__ = "0.0.0+dev"

from hother.streamblocks.adapters import (
    BidirectionalAdapter,
    EventCategory,
    InputAdapterRegistry,
    InputProtocolAdapter,
    OutputProtocolAdapter,
    detect_input_adapter,
)
from hother.streamblocks.core.models import Block, BlockCandidate, ExtractedBlock
from hother.streamblocks.core.parsing import ParseStrategy, parse_as_json, parse_as_yaml
from hother.streamblocks.core.processor import StreamBlockProcessor, StreamState
from hother.streamblocks.core.protocol_processor import ProtocolStreamProcessor
from hother.streamblocks.core.registry import MetadataValidationFailureMode, Registry, ValidationResult
from hother.streamblocks.core.types import (
    BaseContent,
    BaseEvent,
    BaseMetadata,
    BlockContentDeltaEvent,
    BlockContentEndEvent,
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
    # Adapters (new bidirectional system)
    "BidirectionalAdapter",
    "EventCategory",
    "InputAdapterRegistry",
    "InputProtocolAdapter",
    "OutputProtocolAdapter",
    "detect_input_adapter",
    # Core models
    "BaseContent",
    "BaseEvent",
    "BaseMetadata",
    "Block",
    "BlockCandidate",
    # Block events
    "BlockContentDeltaEvent",
    "BlockContentEndEvent",
    "BlockEndEvent",
    "BlockErrorCode",
    "BlockErrorEvent",
    "BlockHeaderDeltaEvent",
    "BlockMetadataDeltaEvent",
    "BlockMetadataEndEvent",
    "BlockStartEvent",
    "BlockState",
    "CustomEvent",
    # Built-in syntaxes
    "DelimiterFrontmatterSyntax",
    "DelimiterPreambleSyntax",
    # Core types
    "DetectionResult",
    "Event",
    "EventType",
    "ExtractedBlock",
    "MarkdownFrontmatterSyntax",
    # Validation
    "MetadataValidationFailureMode",
    "ParseResult",
    # Parsing
    "ParseStrategy",
    # Processors
    "ProtocolStreamProcessor",
    # Core components
    "Registry",
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
