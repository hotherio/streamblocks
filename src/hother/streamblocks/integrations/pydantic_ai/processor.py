"""Stream processor for PydanticAI agent output."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from hother.streamblocks.core.processor import ProcessorConfig, StreamBlockProcessor

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, AsyncIterator, Callable

    from hother.streamblocks.core.registry import Registry
    from hother.streamblocks.core.types import BaseEvent


class AgentStreamProcessor(StreamBlockProcessor):
    """Enhanced processor designed to work with PydanticAI agent streaming output.

    This processor is optimized for handling streaming text from AI agents,
    with special handling for partial blocks and real-time extraction.
    """

    def __init__(
        self,
        registry: Registry,
        config: ProcessorConfig | None = None,
        *,
        enable_partial_blocks: bool = True,
    ) -> None:
        """Initialize the agent stream processor.

        Args:
            registry: Registry with a single syntax
            config: Configuration object for processor settings
            enable_partial_blocks: Whether to emit section delta events for partial blocks
        """
        super().__init__(registry, config=config)
        self.enable_partial_blocks = enable_partial_blocks

    async def process_agent_stream(self, agent_stream: AsyncIterator[str]) -> AsyncGenerator[str | BaseEvent]:
        """Process streaming output from a PydanticAI agent.

        This method is specifically designed to handle the streaming output
        from agent.run_stream() or similar agent streaming methods.

        Args:
            agent_stream: Async iterator from agent streaming (e.g., stream_text())

        Yields:
            Mixed stream of:
            - Original text chunks (if emit_original_events=True)
            - Event objects as blocks are detected and extracted
        """
        async for event in self.process_stream(agent_stream):
            yield event

    async def process_agent_with_events(
        self,
        agent_stream: AsyncIterator[str],
        event_handler: Callable[[str | BaseEvent], Any] | None = None,
    ) -> AsyncGenerator[str | BaseEvent]:
        """Process agent stream with optional event handler for agent-specific events.

        This allows handling both StreamBlocks events and PydanticAI events
        in a unified manner.

        Args:
            agent_stream: Async iterator from agent streaming
            event_handler: Optional callback for handling events (both text chunks and Events)

        Yields:
            Mixed stream of:
            - Original text chunks (if emit_original_events=True)
            - Event objects with enhanced metadata
        """
        async for event in self.process_agent_stream(agent_stream):
            # Call event handler if provided
            if event_handler:
                await event_handler(event)

            # Always yield the event
            yield event
