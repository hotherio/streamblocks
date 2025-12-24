"""Built-in output adapter that emits native StreamBlocks events."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from hother.streamblocks.core.types import BaseEvent


class StreamBlocksOutputAdapter:
    """Output adapter that emits native StreamBlocks events.

    This is the default output adapter that passes through StreamBlocks events
    unchanged. Use this when you want to receive the native StreamBlocks event
    types rather than converting them to another protocol format.

    Example:
        >>> adapter = StreamBlocksOutputAdapter()
        >>> event = BlockEndEvent(...)
        >>> adapter.to_protocol_event(event)
        BlockEndEvent(...)  # Same event passed through
    """

    def to_protocol_event(
        self,
        event: BaseEvent,
    ) -> BaseEvent:
        """Pass through StreamBlocks event unchanged.

        Args:
            event: StreamBlocks event

        Returns:
            The same event unchanged
        """
        return event

    def passthrough(self, original_event: Any) -> None:
        """Passthrough not supported for native StreamBlocks output.

        Plain text/identity input has no passthrough events.

        Args:
            original_event: Original input event

        Returns:
            None - passthrough not applicable
        """
        return
