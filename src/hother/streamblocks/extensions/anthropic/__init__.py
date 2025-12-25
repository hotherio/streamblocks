"""Anthropic extension for StreamBlocks.

This extension provides input adapters for Anthropic message streams.

Importing this module registers the AnthropicInputAdapter for auto-detection.

Example:
    >>> # Import to enable auto-detection
    >>> import hother.streamblocks.extensions.anthropic
    >>>
    >>> # Auto-detect from Anthropic stream
    >>> processor = ProtocolStreamProcessor(registry)
    >>> async for event in processor.process_stream(anthropic_stream):
    ...     print(event)
    >>>
    >>> # Or use convenience factory
    >>> from hother.streamblocks.extensions.anthropic import create_anthropic_processor
    >>> processor = create_anthropic_processor(registry)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from hother.streamblocks.adapters.categories import EventCategory
from hother.streamblocks.adapters.detection import InputAdapterRegistry

# Import Anthropic types - required for this extension
try:
    from anthropic.types import (
        ContentBlockDeltaEvent,
        MessageDeltaEvent,
        MessageStopEvent,
        TextDelta,
    )

    # Union of all event types we handle
    AnthropicEvent = ContentBlockDeltaEvent | MessageDeltaEvent | MessageStopEvent
except ImportError as _import_error:
    _msg = 'Please install `anthropic` to use the Anthropic adapter, you can use the `anthropic` optional group — `pip install "streamblocks[anthropic]"`'
    raise ImportError(_msg) from _import_error

if TYPE_CHECKING:
    from hother.streamblocks.core.protocol_processor import ProtocolStreamProcessor
    from hother.streamblocks.core.registry import Registry
    from hother.streamblocks.core.types import BaseEvent

# Event type constants to avoid magic strings
_TEXT_CONTENT_EVENT = "content_block_delta"
_MESSAGE_STOP_EVENT = "message_stop"
_MESSAGE_DELTA_EVENT = "message_delta"


@InputAdapterRegistry.register(module_prefix="anthropic.")
class AnthropicInputAdapter:
    """Input adapter for Anthropic message streams.

    Handles event-based streaming from anthropic.MessageStream.

    Anthropic uses different event types:
    - content_block_delta: Contains text deltas (TEXT_CONTENT)
    - message_delta: Contains usage information (PASSTHROUGH)
    - message_stop: Signals stream completion (PASSTHROUGH)
    - Other events: PASSTHROUGH

    Example:
        >>> from anthropic import AsyncAnthropic
        >>> adapter = AnthropicInputAdapter()
        >>>
        >>> client = AsyncAnthropic()
        >>> async with client.messages.stream(...) as stream:
        ...     async for event in stream:
        ...         text = adapter.extract_text(event)
        ...         if text:
        ...             print(text, end='', flush=True)
        ...         if adapter.is_complete(event):
        ...             print("\\nDone!")
    """

    native_module_prefix: ClassVar[str] = "anthropic."

    def categorize(self, event: AnthropicEvent) -> EventCategory:
        """Categorize event based on type.

        Args:
            event: Anthropic event

        Returns:
            TEXT_CONTENT for content_block_delta events, PASSTHROUGH for others
        """
        if isinstance(event, ContentBlockDeltaEvent):
            return EventCategory.TEXT_CONTENT
        # Other event types pass through
        return EventCategory.PASSTHROUGH

    def extract_text(self, event: AnthropicEvent) -> str | None:
        """Extract text from content_block_delta events.

        Args:
            event: Anthropic event

        Returns:
            Delta text if present, None otherwise
        """
        if isinstance(event, ContentBlockDeltaEvent):
            delta = event.delta
            if isinstance(delta, TextDelta):
                return delta.text
        return None

    def is_complete(self, event: AnthropicEvent) -> bool:
        """Check for message_stop event.

        Args:
            event: Anthropic event

        Returns:
            True if this is the message_stop event
        """
        return isinstance(event, MessageStopEvent)

    def get_metadata(self, event: AnthropicEvent) -> dict[str, Any] | None:
        """Extract stop reason and usage information.

        Args:
            event: Anthropic event

        Returns:
            Dictionary with stop_reason or usage if present
        """
        metadata: dict[str, Any] = {}

        if isinstance(event, MessageStopEvent):
            # MessageStopEvent doesn't have stop_reason, it's in MessageDeltaEvent
            return None

        if isinstance(event, MessageDeltaEvent):
            if event.usage:
                metadata["usage"] = event.usage
            return metadata if metadata else None

        return None


# Register additional module paths for Anthropic
InputAdapterRegistry.register_module("anthropic.types", AnthropicInputAdapter)
InputAdapterRegistry.register_module("anthropic.lib", AnthropicInputAdapter)


def create_anthropic_processor(
    registry: Registry,
) -> ProtocolStreamProcessor[Any, BaseEvent]:
    """Create processor pre-configured for Anthropic streams.

    This is a convenience factory that creates a ProtocolStreamProcessor
    with AnthropicInputAdapter and StreamBlocksOutputAdapter.

    Args:
        registry: Registry with syntax and block definitions

    Returns:
        Pre-configured processor for Anthropic streams

    Example:
        >>> from hother.streamblocks.extensions.anthropic import create_anthropic_processor
        >>> processor = create_anthropic_processor(registry)
        >>> async for event in processor.process_stream(anthropic_stream):
        ...     if isinstance(event, BlockExtractedEvent):
        ...         print(f"Block: {event.block.metadata.id}")
    """
    from hother.streamblocks.adapters.output import StreamBlocksOutputAdapter
    from hother.streamblocks.core.protocol_processor import ProtocolStreamProcessor

    return ProtocolStreamProcessor(
        registry,
        input_adapter=AnthropicInputAdapter(),
        output_adapter=StreamBlocksOutputAdapter(),
    )


__all__ = [
    "AnthropicInputAdapter",
    "create_anthropic_processor",
]
