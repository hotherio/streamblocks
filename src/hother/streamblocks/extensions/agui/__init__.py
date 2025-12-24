"""AG-UI extension for StreamBlocks.

This extension provides bidirectional adapters for the AG-UI protocol.

AG-UI is an event-based protocol for agent-to-frontend communication with
event types for lifecycle, text messages, tool calls, and state management.

Importing this module registers the AGUIInputAdapter for auto-detection.

Example:
    >>> # Import to enable auto-detection
    >>> import hother.streamblocks.extensions.agui
    >>>
    >>> # Auto-detect from AG-UI stream
    >>> processor = ProtocolStreamProcessor(registry)
    >>> async for event in processor.process_stream(agui_stream):
    ...     print(event)
    >>>
    >>> # Bidirectional: AG-UI in, AG-UI out
    >>> from hother.streamblocks.extensions.agui import (
    ...     create_agui_bidirectional_processor,
    ...     AGUIEventFilter,
    ... )
    >>> processor = create_agui_bidirectional_processor(
    ...     registry,
    ...     event_filter=AGUIEventFilter.BLOCKS_WITH_PROGRESS,
    ... )
    >>> async for event in processor.process_stream(agui_stream):
    ...     # event is an AG-UI event (dict format)
    ...     if event["type"] == "CUSTOM":
    ...         handle_streamblocks_event(event)
    ...     else:
    ...         forward_to_frontend(event)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from hother.streamblocks.extensions.agui.filters import AGUIEventFilter
from hother.streamblocks.extensions.agui.input_adapter import AGUIInputAdapter
from hother.streamblocks.extensions.agui.output_adapter import AGUIOutputAdapter

if TYPE_CHECKING:
    from hother.streamblocks.core.protocol_processor import ProtocolStreamProcessor
    from hother.streamblocks.core.registry import Registry
    from hother.streamblocks.core.types import BaseEvent


def create_agui_processor(
    registry: Registry,
) -> ProtocolStreamProcessor[Any, BaseEvent]:
    """Create processor for AG-UI → StreamBlocks (unidirectional).

    This processor takes AG-UI events as input and emits native
    StreamBlocks events.

    Args:
        registry: Registry with syntax and block definitions

    Returns:
        Pre-configured processor for AG-UI input, StreamBlocks output

    Example:
        >>> from hother.streamblocks.extensions.agui import create_agui_processor
        >>> processor = create_agui_processor(registry)
        >>> async for event in processor.process_stream(agui_stream):
        ...     if isinstance(event, BlockExtractedEvent):
        ...         print(f"Block: {event.block.metadata.id}")
    """
    from hother.streamblocks.adapters.output import StreamBlocksOutputAdapter
    from hother.streamblocks.core.protocol_processor import ProtocolStreamProcessor

    return ProtocolStreamProcessor(
        registry,
        input_adapter=AGUIInputAdapter(),
        output_adapter=StreamBlocksOutputAdapter(),
    )


def create_agui_bidirectional_processor(
    registry: Registry,
    event_filter: AGUIEventFilter = AGUIEventFilter.ALL,
) -> ProtocolStreamProcessor[Any, dict[str, Any]]:
    """Create processor for AG-UI → AG-UI (bidirectional).

    This processor takes AG-UI events as input and emits AG-UI events
    as output. StreamBlocks events are converted to AG-UI CustomEvent
    format.

    Args:
        registry: Registry with syntax and block definitions
        event_filter: Filter to control which StreamBlocks events are emitted

    Returns:
        Pre-configured processor for AG-UI input and output

    Example:
        >>> from hother.streamblocks.extensions.agui import (
        ...     create_agui_bidirectional_processor,
        ...     AGUIEventFilter,
        ... )
        >>> processor = create_agui_bidirectional_processor(
        ...     registry,
        ...     event_filter=AGUIEventFilter.BLOCKS_WITH_PROGRESS,
        ... )
        >>> async for event in processor.process_stream(agui_stream):
        ...     if event["type"] == "CUSTOM":
        ...         if event["name"] == "streamblocks.block_extracted":
        ...             handle_block(event["value"])
        ...     else:
        ...         # Passthrough: lifecycle, tool calls, state
        ...         forward_to_frontend(event)
    """
    from hother.streamblocks.core.protocol_processor import ProtocolStreamProcessor

    return ProtocolStreamProcessor(
        registry,
        input_adapter=AGUIInputAdapter(),
        output_adapter=AGUIOutputAdapter(event_filter=event_filter),
    )


__all__ = [
    "AGUIEventFilter",
    "AGUIInputAdapter",
    "AGUIOutputAdapter",
    "create_agui_bidirectional_processor",
    "create_agui_processor",
]
