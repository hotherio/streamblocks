"""AG-UI input adapter for StreamBlocks."""

from __future__ import annotations

from typing import Any, ClassVar

from hother.streamblocks.adapters.categories import EventCategory
from hother.streamblocks.adapters.detection import InputAdapterRegistry

# Import AG-UI types - required for this extension
try:
    from ag_ui.core import (
        BaseEvent,
        RunFinishedEvent,
        TextMessageChunkEvent,
        TextMessageContentEvent,
    )

    # Union of text content event types
    AGUITextEvent = TextMessageContentEvent | TextMessageChunkEvent
except ImportError as _import_error:  # pragma: no cover
    _msg = 'Please install `ag-ui` to use the AG-UI adapter, you can use the `agui` optional group — `pip install "streamblocks[agui]"`'
    raise ImportError(_msg) from _import_error


@InputAdapterRegistry.register(module_prefix="ag_ui.")
class AGUIInputAdapter:
    """Input adapter for AG-UI protocol events.

    Handles event-based streaming from AG-UI protocol.

    AG-UI Event Categories:
    - TEXT_MESSAGE_CONTENT, TEXT_MESSAGE_CHUNK: TEXT_CONTENT (has text)
    - All other events: PASSTHROUGH (lifecycle, tool calls, state)

    Example:
        >>> adapter = AGUIInputAdapter()
        >>>
        >>> async for event in agui_stream:
        ...     category = adapter.categorize(event)
        ...     if category == EventCategory.TEXT_CONTENT:
        ...         text = adapter.extract_text(event)
        ...         print(text, end='', flush=True)
    """

    native_module_prefix: ClassVar[str] = "ag_ui."

    def categorize(self, event: BaseEvent) -> EventCategory:
        """Categorize event based on type.

        Args:
            event: AG-UI BaseEvent

        Returns:
            TEXT_CONTENT for text message events, PASSTHROUGH for others
        """
        if isinstance(event, (TextMessageContentEvent, TextMessageChunkEvent)):
            return EventCategory.TEXT_CONTENT

        # All other events (lifecycle, tool calls, state) pass through
        return EventCategory.PASSTHROUGH

    def extract_text(self, event: BaseEvent) -> str | None:
        """Extract text from TEXT_CONTENT events.

        Args:
            event: AG-UI BaseEvent

        Returns:
            Delta text if TEXT_MESSAGE_CONTENT or TEXT_MESSAGE_CHUNK
        """
        if isinstance(event, (TextMessageContentEvent, TextMessageChunkEvent)):
            return event.delta

        return None

    def is_complete(self, event: BaseEvent) -> bool:
        """Check for RUN_FINISHED event.

        Args:
            event: AG-UI BaseEvent

        Returns:
            True if this is the RUN_FINISHED event
        """
        return isinstance(event, RunFinishedEvent)

    def get_metadata(self, event: BaseEvent) -> dict[str, Any] | None:
        """Extract protocol metadata.

        Args:
            event: AG-UI BaseEvent

        Returns:
            Dictionary with event_type and timestamp if available
        """
        # Get event type as string
        event_type_str = event.type.value if event.type else None

        metadata: dict[str, Any] = {"event_type": event_type_str}

        if event.timestamp is not None:
            metadata["timestamp"] = event.timestamp

        return metadata
