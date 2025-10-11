"""Stream processor for PydanticAI agent output."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from hother.streamblocks.core.processor import StreamBlockProcessor

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, AsyncIterator, Callable

    from hother.streamblocks.core.registry import Registry
    from hother.streamblocks.core.types import StreamEvent


class AgentStreamProcessor(StreamBlockProcessor):
    """Enhanced processor designed to work with PydanticAI agent streaming output.

    This processor is optimized for handling streaming text from AI agents,
    with special handling for partial blocks and real-time extraction.
    """

    def __init__(
        self,
        registry: Registry,
        lines_buffer: int = 5,
        max_line_length: int = 16_384,
        max_block_size: int = 1_048_576,
        enable_partial_blocks: bool = True,
    ) -> None:
        """Initialize the agent stream processor.

        Args:
            registry: Registry with a single syntax
            lines_buffer: Number of lines to keep in buffer
            max_line_length: Maximum line length before truncation
            max_block_size: Maximum block size in bytes
            enable_partial_blocks: Whether to emit BLOCK_DELTA events for partial blocks
        """
        super().__init__(
            registry,
            lines_buffer=lines_buffer,
            max_line_length=max_line_length,
            max_block_size=max_block_size,
        )
        self.enable_partial_blocks = enable_partial_blocks

    async def process_agent_stream(
        self, agent_stream: AsyncIterator[str]
    ) -> AsyncGenerator[str | StreamEvent[Any, Any]]:
        """Process streaming output from a PydanticAI agent.

        This method is specifically designed to handle the streaming output
        from agent.run_stream() or similar agent streaming methods.

        Args:
            agent_stream: Async iterator from agent streaming (e.g., stream_text())

        Yields:
            Mixed stream of:
            - Original text chunks (if emit_original_events=True)
            - StreamEvent objects as blocks are detected and extracted
        """
        async for event in self.process_stream(agent_stream):
            yield event

    async def process_agent_with_events(
        self,
        agent_stream: AsyncIterator[str],
        event_handler: Callable[[str | StreamEvent[Any, Any]], Any] | None = None,
    ) -> AsyncGenerator[str | StreamEvent[Any, Any]]:
        """Process agent stream with optional event handler for agent-specific events.

        This allows handling both StreamBlocks events and PydanticAI events
        in a unified manner.

        Args:
            agent_stream: Async iterator from agent streaming
            event_handler: Optional callback for handling events (both text chunks and StreamEvents)

        Yields:
            Mixed stream of:
            - Original text chunks (if emit_original_events=True)
            - StreamEvent objects with enhanced metadata
        """
        async for event in self.process_agent_stream(agent_stream):
            # Call event handler if provided
            if event_handler:
                await event_handler(event)

            # Always yield the event
            yield event
