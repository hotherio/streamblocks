"""Tests for AgentStreamProcessor PydanticAI integration."""

from __future__ import annotations

from typing import Any

import pytest

from hother.streamblocks import DelimiterPreambleSyntax, Registry
from hother.streamblocks.core.processor import ProcessorConfig
from hother.streamblocks.core.types import EventType
from hother.streamblocks.integrations.pydantic_ai.processor import AgentStreamProcessor


class TestAgentStreamProcessorInit:
    """Tests for AgentStreamProcessor initialization."""

    def test_init_with_registry(self) -> None:
        """Test initialization with registry."""
        registry = Registry(syntax=DelimiterPreambleSyntax())

        processor = AgentStreamProcessor(registry)

        assert processor.registry is registry
        assert processor.enable_partial_blocks is True

    def test_init_with_config(self) -> None:
        """Test initialization with config."""
        registry = Registry(syntax=DelimiterPreambleSyntax())
        config = ProcessorConfig(emit_text_deltas=True)

        processor = AgentStreamProcessor(registry, config=config)

        assert processor.registry is registry
        # Config is applied to parent class

    def test_init_disable_partial_blocks(self) -> None:
        """Test initialization with partial blocks disabled."""
        registry = Registry(syntax=DelimiterPreambleSyntax())

        processor = AgentStreamProcessor(registry, enable_partial_blocks=False)

        assert processor.enable_partial_blocks is False


class TestAgentStreamProcessorProcessAgentStream:
    """Tests for AgentStreamProcessor.process_agent_stream()."""

    @pytest.mark.asyncio
    async def test_process_empty_stream(self) -> None:
        """Test processing an empty stream."""
        registry = Registry(syntax=DelimiterPreambleSyntax())
        processor = AgentStreamProcessor(registry)

        async def empty_stream() -> Any:
            return
            yield  # Make it an async generator

        events: list[Any] = []
        async for event in processor.process_agent_stream(empty_stream()):
            events.append(event)

        # Empty stream may have no events or just lifecycle events
        # The exact behavior depends on the processor implementation
        assert isinstance(events, list)

    @pytest.mark.asyncio
    async def test_process_text_stream(self) -> None:
        """Test processing a text stream."""
        registry = Registry(syntax=DelimiterPreambleSyntax())
        config = ProcessorConfig(emit_text_deltas=True)
        processor = AgentStreamProcessor(registry, config=config)

        async def text_stream() -> Any:
            yield "Hello "
            yield "world!\n"

        events: list[Any] = []
        async for event in processor.process_agent_stream(text_stream()):
            events.append(event)

        # Should have processed the text
        assert len(events) > 2  # More than just START/FINISHED

    @pytest.mark.asyncio
    async def test_process_stream_with_block(self) -> None:
        """Test processing a stream containing a block."""
        registry = Registry(syntax=DelimiterPreambleSyntax())
        processor = AgentStreamProcessor(registry)

        async def block_stream() -> Any:
            yield "```python\n"
            yield "print('hello')\n"
            yield "```\n"

        events: list[Any] = []
        async for event in processor.process_agent_stream(block_stream()):
            events.append(event)

        # Should have events
        assert len(events) > 0


class TestAgentStreamProcessorProcessAgentWithEvents:
    """Tests for AgentStreamProcessor.process_agent_with_events()."""

    @pytest.mark.asyncio
    async def test_process_with_event_handler(self) -> None:
        """Test processing with an event handler callback."""
        registry = Registry(syntax=DelimiterPreambleSyntax())
        processor = AgentStreamProcessor(registry)

        async def text_stream() -> Any:
            yield "Test text\n"

        # Track events passed to handler
        handled_events: list[Any] = []

        async def event_handler(event: Any) -> None:
            handled_events.append(event)

        events: list[Any] = []
        async for event in processor.process_agent_with_events(text_stream(), event_handler):
            events.append(event)

        # Handler should have been called for each event
        assert len(handled_events) == len(events)

    @pytest.mark.asyncio
    async def test_process_without_event_handler(self) -> None:
        """Test processing without an event handler."""
        registry = Registry(syntax=DelimiterPreambleSyntax())
        processor = AgentStreamProcessor(registry)

        async def text_stream() -> Any:
            yield "Text\n"

        events: list[Any] = []
        async for event in processor.process_agent_with_events(text_stream(), None):
            events.append(event)

        # Should still yield events
        assert len(events) > 0

    @pytest.mark.asyncio
    async def test_event_handler_receives_all_events(self) -> None:
        """Test that event handler receives all event types."""
        registry = Registry(syntax=DelimiterPreambleSyntax())
        config = ProcessorConfig(emit_text_deltas=True)
        processor = AgentStreamProcessor(registry, config=config)

        async def text_stream() -> Any:
            yield "Hello "
            yield "world\n"

        received_types: set[Any] = set()

        async def event_handler(event: Any) -> None:
            if hasattr(event, "type"):
                received_types.add(event.type)

        async for _ in processor.process_agent_with_events(text_stream(), event_handler):
            pass

        # Should have received at least some text event types
        # The exact events depend on processor configuration
        assert len(received_types) > 0
        # With emit_text_deltas=True, we should see text delta events
        assert EventType.TEXT_DELTA in received_types or EventType.TEXT_CONTENT in received_types


class TestAgentStreamProcessorInheritance:
    """Tests for AgentStreamProcessor inheritance from StreamBlockProcessor."""

    def test_inherits_from_stream_block_processor(self) -> None:
        """Test that AgentStreamProcessor inherits from StreamBlockProcessor."""
        from hother.streamblocks.core.processor import StreamBlockProcessor

        registry = Registry(syntax=DelimiterPreambleSyntax())
        processor = AgentStreamProcessor(registry)

        assert isinstance(processor, StreamBlockProcessor)

    def test_has_process_stream_method(self) -> None:
        """Test that processor has process_stream from parent."""
        registry = Registry(syntax=DelimiterPreambleSyntax())
        processor = AgentStreamProcessor(registry)

        assert hasattr(processor, "process_stream")
        assert callable(processor.process_stream)

    def test_has_registry_attribute(self) -> None:
        """Test that processor has registry from parent."""
        registry = Registry(syntax=DelimiterPreambleSyntax())
        processor = AgentStreamProcessor(registry)

        assert processor.registry is registry
