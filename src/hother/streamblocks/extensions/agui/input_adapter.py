"""AG-UI input adapter for StreamBlocks."""

from __future__ import annotations

from typing import Any

from hother.streamblocks.adapters.categories import EventCategory
from hother.streamblocks.adapters.detection import InputAdapterRegistry

# AG-UI event type constants to avoid magic strings
_TEXT_MESSAGE_CONTENT = "TEXT_MESSAGE_CONTENT"
_TEXT_MESSAGE_CHUNK = "TEXT_MESSAGE_CHUNK"
_RUN_FINISHED = "RUN_FINISHED"


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

    def categorize(self, event: Any) -> EventCategory:
        """Categorize event based on type.

        Args:
            event: AG-UI BaseEvent

        Returns:
            TEXT_CONTENT for text message events, PASSTHROUGH for others
        """
        event_type = getattr(event, "type", None)
        if event_type is None:
            return EventCategory.PASSTHROUGH

        # Handle both string and enum event types
        event_type_str = event_type.value if hasattr(event_type, "value") else event_type

        if event_type_str in (_TEXT_MESSAGE_CONTENT, _TEXT_MESSAGE_CHUNK):
            return EventCategory.TEXT_CONTENT

        # All other events (lifecycle, tool calls, state) pass through
        return EventCategory.PASSTHROUGH

    def extract_text(self, event: Any) -> str | None:
        """Extract text from TEXT_CONTENT events.

        Args:
            event: AG-UI BaseEvent

        Returns:
            Delta text if TEXT_MESSAGE_CONTENT, content if TEXT_MESSAGE_CHUNK
        """
        event_type = getattr(event, "type", None)
        if event_type is None:
            return None

        # Handle both string and enum event types
        event_type_str = event_type.value if hasattr(event_type, "value") else event_type

        if event_type_str == _TEXT_MESSAGE_CONTENT:
            return getattr(event, "delta", None)

        if event_type_str == _TEXT_MESSAGE_CHUNK:
            return getattr(event, "content", None)

        return None

    def is_complete(self, event: Any) -> bool:
        """Check for RUN_FINISHED event.

        Args:
            event: AG-UI BaseEvent

        Returns:
            True if this is the RUN_FINISHED event
        """
        event_type = getattr(event, "type", None)
        if event_type is None:
            return False

        # Handle both string and enum event types
        event_type_str = event_type.value if hasattr(event_type, "value") else event_type

        return event_type_str == _RUN_FINISHED

    def get_metadata(self, event: Any) -> dict[str, Any] | None:
        """Extract protocol metadata.

        Args:
            event: AG-UI BaseEvent

        Returns:
            Dictionary with event_type and timestamp if available
        """
        event_type = getattr(event, "type", None)

        # Handle both string and enum event types
        event_type_str = event_type.value if hasattr(event_type, "value") and event_type is not None else event_type

        metadata: dict[str, Any] = {"event_type": event_type_str}

        if hasattr(event, "timestamp"):
            metadata["timestamp"] = event.timestamp

        return metadata
