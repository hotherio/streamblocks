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
from hother.streamblocks.core.processor import StreamBlockProcessor
from hother.streamblocks.core.registry import Registry
from hother.streamblocks.core.types import (
    BaseContent,
    BaseMetadata,
    BlockDeltaEvent,
    BlockExtractedEvent,
    BlockOpenedEvent,
    BlockRejectedEvent,
    BlockState,
    DetectionResult,
    EventType,
    ParseResult,
    RawTextEvent,
    StreamEvent,
    TextDeltaEvent,
)
from hother.streamblocks.syntaxes import (
    DEFAULT_SYNTAX,
    DelimiterFrontmatterSyntax,
    DelimiterPreambleSyntax,
    MarkdownFrontmatterSyntax,
    Syntax,
    get_default_syntax,
    reset_default_syntax,
    set_default_syntax,
)

# Rebuild event models to resolve forward references to ExtractedBlock
RawTextEvent.model_rebuild()
TextDeltaEvent.model_rebuild()
BlockOpenedEvent.model_rebuild()
BlockDeltaEvent.model_rebuild()
BlockExtractedEvent.model_rebuild()
BlockRejectedEvent.model_rebuild()

__all__ = [
    # Adapters
    "AdapterDetector",
    "AnthropicAdapter",
    "AttributeAdapter",
    # Core models
    "BaseContent",
    "BaseMetadata",
    "Block",
    "BlockCandidate",
    "BlockDeltaEvent",
    "BlockExtractedEvent",
    "BlockOpenedEvent",
    "BlockRejectedEvent",
    # Core types
    "BlockState",
    "CallableAdapter",
    # Configuration
    "DEFAULT_SYNTAX",
    # Built-in syntaxes
    "DelimiterFrontmatterSyntax",
    "DelimiterPreambleSyntax",
    "DetectionResult",
    "EventType",
    "ExtractedBlock",
    "GeminiAdapter",
    "IdentityAdapter",
    "MarkdownFrontmatterSyntax",
    "OpenAIAdapter",
    "ParseResult",
    # Parsing
    "ParseStrategy",
    "RawTextEvent",
    # Core components
    "Registry",
    "StreamAdapter",
    "StreamBlockProcessor",
    # Events
    "StreamEvent",
    "Syntax",
    "TextDeltaEvent",
    # Configuration functions
    "get_default_syntax",
    # Parsing utilities
    "parse_as_json",
    "parse_as_yaml",
    "reset_default_syntax",
    "set_default_syntax",
]
