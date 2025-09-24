"""Stream processor for PydanticAI agent output."""

from __future__ import annotations

from collections.abc import AsyncGenerator, AsyncIterator
from typing import Any, TypeVar

from streamblocks.core.processor import StreamBlockProcessor
from streamblocks.core.registry import Registry
from streamblocks.core.types import EventType, StreamEvent

TSyntax = TypeVar("TSyntax")


class AgentStreamProcessor(StreamBlockProcessor):
    """Enhanced processor designed to work with PydanticAI agent streaming output.
    
    This processor is optimized for handling streaming text from AI agents,
    with special handling for partial blocks and real-time extraction.
    """
    
    def __init__(
        self,
        registry: Registry[TSyntax],
        lines_buffer: int = 5,
        max_line_length: int = 16_384,
        max_block_size: int = 1_048_576,
        enable_partial_blocks: bool = True,
    ) -> None:
        """Initialize the agent stream processor.
        
        Args:
            registry: Type-specific registry with a single syntax
            lines_buffer: Number of lines to keep in buffer
            max_line_length: Maximum line length before truncation
            max_block_size: Maximum block size in bytes
            enable_partial_blocks: Whether to emit BLOCK_DELTA events for partial blocks
        """
        super().__init__(registry, lines_buffer, max_line_length, max_block_size)
        self.enable_partial_blocks = enable_partial_blocks
        self._agent_stream_active = False
        self._stream_metadata: dict[str, Any] = {}
    
    async def process_agent_stream(
        self,
        agent_stream: AsyncIterator[str],
        stream_metadata: dict[str, Any] | None = None,
    ) -> AsyncGenerator[StreamEvent[Any, Any]]:
        """Process streaming output from a PydanticAI agent.
        
        This method is specifically designed to handle the streaming output
        from agent.run_stream() or similar agent streaming methods.
        
        Args:
            agent_stream: Async iterator from agent streaming (e.g., stream_text())
            stream_metadata: Optional metadata about the agent stream
            
        Yields:
            StreamEvent objects as blocks are detected and extracted
        """
        self._agent_stream_active = True
        self._stream_metadata = stream_metadata or {}
        
        # Add agent stream indicator to events
        async for event in self.process_stream(agent_stream):
            # Enhance events with agent stream metadata
            if event.metadata is None:
                event.metadata = {}
            event.metadata["from_agent"] = True
            if self._stream_metadata:
                event.metadata["agent_info"] = self._stream_metadata
            
            yield event
        
        self._agent_stream_active = False
    
    async def process_agent_with_events(
        self,
        agent_stream: AsyncIterator[str],
        event_handler: callable | None = None,
    ) -> AsyncGenerator[StreamEvent[Any, Any]]:
        """Process agent stream with optional event handler for agent-specific events.
        
        This allows handling both StreamBlocks events and PydanticAI events
        in a unified manner.
        
        Args:
            agent_stream: Async iterator from agent streaming
            event_handler: Optional callback for agent-specific events
            
        Yields:
            StreamEvent objects with enhanced metadata
        """
        async for event in self.process_agent_stream(agent_stream):
            # Call event handler if provided
            if event_handler:
                await event_handler(event)
            
            # Always yield the event
            yield event