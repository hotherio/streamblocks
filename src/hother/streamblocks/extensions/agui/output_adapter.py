"""AG-UI output adapter for StreamBlocks."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from hother.streamblocks.extensions.agui.filters import AGUIEventFilter

if TYPE_CHECKING:
    from hother.streamblocks.core.types import (
        BaseContent,
        BaseMetadata,
        StreamEvent,
    )


class AGUIOutputAdapter:
    """Output adapter for AG-UI protocol events.

    Transforms StreamBlocks events into AG-UI CustomEvent format.

    StreamBlocks events are mapped to AG-UI as follows:
    - TextDeltaEvent, RawTextEvent → TextMessageContentEvent
    - BlockOpenedEvent → CustomEvent(name="streamblocks.block_opened")
    - BlockDeltaEvent → CustomEvent(name="streamblocks.block_delta")
    - BlockExtractedEvent → CustomEvent(name="streamblocks.block_extracted")
    - BlockRejectedEvent → CustomEvent(name="streamblocks.block_rejected")

    Passthrough events (AG-UI events from input) are passed through unchanged.

    Example:
        >>> adapter = AGUIOutputAdapter(event_filter=AGUIEventFilter.BLOCKS_WITH_PROGRESS)
        >>>
        >>> # Convert StreamBlocks event to AG-UI event
        >>> agui_event = adapter.to_protocol_event(block_extracted_event)
        >>>
        >>> # Pass through AG-UI events
        >>> original = adapter.passthrough(run_started_event)
    """

    def __init__(
        self,
        event_filter: AGUIEventFilter = AGUIEventFilter.ALL,
    ) -> None:
        """Initialize AG-UI output adapter.

        Args:
            event_filter: Filter to control which StreamBlocks events are emitted
        """
        self.event_filter = event_filter
        self._message_id: str | None = None

    def to_protocol_event(
        self,
        event: StreamEvent[BaseMetadata, BaseContent],
    ) -> dict[str, Any] | None:
        """Convert StreamBlocks event to AG-UI event format.

        Returns a dictionary representation of the AG-UI event that can be
        serialized or converted to the actual AG-UI event type.

        Args:
            event: StreamBlocks event

        Returns:
            Dictionary representing AG-UI event, or None if filtered out

        Note:
            Returns dict rather than actual AG-UI types to avoid requiring
            ag-ui-protocol as a runtime dependency.
        """
        from hother.streamblocks.core.types import (
            BlockDeltaEvent,
            BlockExtractedEvent,
            BlockOpenedEvent,
            BlockRejectedEvent,
            RawTextEvent,
            TextDeltaEvent,
        )

        # Check filter first
        if not self._should_emit(event):
            return None

        if isinstance(event, TextDeltaEvent):
            return {
                "type": "TEXT_MESSAGE_CONTENT",
                "message_id": self._ensure_message_id(),
                "delta": event.delta,
            }

        if isinstance(event, RawTextEvent):
            return {
                "type": "TEXT_MESSAGE_CONTENT",
                "message_id": self._ensure_message_id(),
                "delta": event.data,
            }

        if isinstance(event, BlockOpenedEvent):
            return {
                "type": "CUSTOM",
                "name": "streamblocks.block_opened",
                "value": {
                    "syntax": event.syntax,
                    "start_line": event.start_line,
                    "inline_metadata": event.inline_metadata,
                },
            }

        if isinstance(event, BlockDeltaEvent):
            return {
                "type": "CUSTOM",
                "name": "streamblocks.block_delta",
                "value": {
                    "syntax": event.syntax,
                    "section": event.section,
                    "delta": event.delta,
                    "start_line": event.start_line,
                    "current_line": event.current_line,
                },
            }

        if isinstance(event, BlockExtractedEvent):
            return {
                "type": "CUSTOM",
                "name": "streamblocks.block_extracted",
                "value": {
                    "block_id": event.block.hash_id,
                    "block_type": event.block.metadata.block_type,
                    "syntax": event.block.syntax_name,
                    "metadata": event.block.metadata.model_dump(),
                    "content": event.block.content.model_dump(),
                    "line_start": event.block.line_start,
                    "line_end": event.block.line_end,
                },
            }

        if isinstance(event, BlockRejectedEvent):
            return {
                "type": "CUSTOM",
                "name": "streamblocks.block_rejected",
                "value": {
                    "reason": event.reason,
                    "syntax": event.syntax,
                    "start_line": event.start_line,
                    "end_line": event.end_line,
                },
            }

        return None

    def passthrough(self, original_event: Any) -> Any:
        """Handle passthrough events.

        For AG-UI events, passes them through unchanged.

        Args:
            original_event: Original input event

        Returns:
            The original event unchanged
        """
        # If it's an AG-UI event (dict or object with type), pass through
        if isinstance(original_event, dict) and "type" in original_event:
            return original_event

        if hasattr(original_event, "type"):
            return original_event

        # For other events, wrap in a raw event format
        return {
            "type": "RAW",
            "event": original_event,
        }

    def _should_emit(
        self,
        event: StreamEvent[BaseMetadata, BaseContent],
    ) -> bool:
        """Check if event passes the filter.

        Args:
            event: StreamBlocks event

        Returns:
            True if event should be emitted
        """
        from hother.streamblocks.core.types import (
            BlockDeltaEvent,
            BlockExtractedEvent,
            BlockOpenedEvent,
            BlockRejectedEvent,
            RawTextEvent,
            TextDeltaEvent,
        )

        if isinstance(event, RawTextEvent):
            return AGUIEventFilter.RAW_TEXT in self.event_filter

        if isinstance(event, TextDeltaEvent):
            return AGUIEventFilter.TEXT_DELTA in self.event_filter

        if isinstance(event, BlockOpenedEvent):
            return AGUIEventFilter.BLOCK_OPENED in self.event_filter

        if isinstance(event, BlockDeltaEvent):
            return AGUIEventFilter.BLOCK_DELTA in self.event_filter

        if isinstance(event, BlockExtractedEvent):
            return AGUIEventFilter.BLOCK_EXTRACTED in self.event_filter

        if isinstance(event, BlockRejectedEvent):
            return AGUIEventFilter.BLOCK_REJECTED in self.event_filter

        return True

    def _ensure_message_id(self) -> str:
        """Generate or reuse message ID for text content events.

        Returns:
            Message ID string
        """
        if self._message_id is None:
            self._message_id = str(uuid.uuid4())
        return self._message_id

    def reset_message_id(self) -> None:
        """Reset message ID for new conversation turn."""
        self._message_id = None
