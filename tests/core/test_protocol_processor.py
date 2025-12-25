"""Tests for ProtocolStreamProcessor."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from hother.streamblocks import DelimiterPreambleSyntax, Registry
from hother.streamblocks.adapters.categories import EventCategory
from hother.streamblocks.adapters.input import IdentityInputAdapter
from hother.streamblocks.adapters.output import StreamBlocksOutputAdapter
from hother.streamblocks.core.processor import ProcessorConfig
from hother.streamblocks.core.protocol_processor import ProtocolStreamProcessor
from hother.streamblocks.core.types import (
    BlockEndEvent,
    BlockStartEvent,
    TextContentEvent,
    TextDeltaEvent,
)


class MockInputAdapter:
    """Mock input adapter for testing."""

    def __init__(
        self,
        category: EventCategory = EventCategory.TEXT_CONTENT,
        text: str | None = "test text",
    ) -> None:
        """Initialize with configurable category and text."""
        self._category = category
        self._text = text

    def categorize(self, event: Any) -> EventCategory:
        """Return configured category."""
        return self._category

    def extract_text(self, event: Any) -> str | None:
        """Return configured text."""
        return self._text

    def get_metadata(self, event: Any) -> dict[str, Any] | None:
        """Return None metadata."""
        return None

    def is_complete(self, event: Any) -> bool:
        """Return False for completion check."""
        return False


class MockOutputAdapter:
    """Mock output adapter for testing."""

    def __init__(
        self,
        output: Any | None = None,
        passthrough_output: Any | None = None,
    ) -> None:
        """Initialize with configurable outputs."""
        self._output = output
        self._passthrough_output = passthrough_output

    def to_protocol_event(self, event: Any) -> Any | None:
        """Return configured output or the event itself."""
        if self._output is not None:
            return self._output
        return {"type": "transformed", "original": event}

    def passthrough(self, original_event: Any) -> Any | None:
        """Return configured passthrough output."""
        return self._passthrough_output


class NoneOutputAdapter:
    """Mock output adapter that returns None for all events."""

    def to_protocol_event(self, event: Any) -> None:
        """Return None for all events."""
        return

    def passthrough(self, original_event: Any) -> None:
        """Return None for passthrough."""
        return


class TestProtocolStreamProcessorInit:
    """Tests for ProtocolStreamProcessor initialization."""

    def test_init_with_registry_only(self) -> None:
        """Test initialization with only registry."""
        registry = Registry(syntax=DelimiterPreambleSyntax())

        processor = ProtocolStreamProcessor(registry)

        assert processor.registry is registry
        assert processor.input_adapter is None
        assert isinstance(processor.output_adapter, StreamBlocksOutputAdapter)
        assert processor.was_auto_detected is False

    def test_init_with_input_adapter(self) -> None:
        """Test initialization with input adapter."""
        registry = Registry(syntax=DelimiterPreambleSyntax())
        input_adapter = IdentityInputAdapter()

        processor = ProtocolStreamProcessor(registry, input_adapter=input_adapter)

        assert processor.input_adapter is input_adapter
        assert processor.was_auto_detected is False

    def test_init_with_output_adapter(self) -> None:
        """Test initialization with output adapter."""
        registry = Registry(syntax=DelimiterPreambleSyntax())
        output_adapter = MockOutputAdapter()

        processor = ProtocolStreamProcessor(registry, output_adapter=output_adapter)

        assert processor.output_adapter is output_adapter

    def test_init_with_both_adapters(self) -> None:
        """Test initialization with both adapters."""
        registry = Registry(syntax=DelimiterPreambleSyntax())
        input_adapter = IdentityInputAdapter()
        output_adapter = MockOutputAdapter()

        processor = ProtocolStreamProcessor(
            registry,
            input_adapter=input_adapter,
            output_adapter=output_adapter,
        )

        assert processor.input_adapter is input_adapter
        assert processor.output_adapter is output_adapter

    def test_init_with_config(self) -> None:
        """Test initialization with custom config."""
        registry = Registry(syntax=DelimiterPreambleSyntax())
        config = ProcessorConfig(emit_text_deltas=True)

        processor = ProtocolStreamProcessor(registry, config=config)

        # Config should be applied (internal state)
        assert processor._config is config

    def test_init_with_logger(self) -> None:
        """Test initialization with logger."""
        registry = Registry(syntax=DelimiterPreambleSyntax())
        mock_logger = MagicMock()

        processor = ProtocolStreamProcessor(registry, logger=mock_logger)

        assert processor._core_processor.logger is mock_logger

    def test_init_default_config_disables_emit_original_events(self) -> None:
        """Test that default config disables emit_original_events."""
        registry = Registry(syntax=DelimiterPreambleSyntax())

        processor = ProtocolStreamProcessor(registry)

        assert processor._config.emit_original_events is False
        assert processor._config.auto_detect_adapter is False


class TestProtocolStreamProcessorProperties:
    """Tests for ProtocolStreamProcessor properties."""

    def test_was_auto_detected_initially_false(self) -> None:
        """Test was_auto_detected is False initially."""
        registry = Registry(syntax=DelimiterPreambleSyntax())
        processor = ProtocolStreamProcessor(registry)

        assert processor.was_auto_detected is False

    def test_input_adapter_initially_none(self) -> None:
        """Test input_adapter is None when not provided."""
        registry = Registry(syntax=DelimiterPreambleSyntax())
        processor = ProtocolStreamProcessor(registry)

        assert processor.input_adapter is None

    def test_output_adapter_has_default(self) -> None:
        """Test output_adapter has default value."""
        registry = Registry(syntax=DelimiterPreambleSyntax())
        processor = ProtocolStreamProcessor(registry)

        assert processor.output_adapter is not None
        assert isinstance(processor.output_adapter, StreamBlocksOutputAdapter)


class TestProtocolStreamProcessorProcessChunk:
    """Tests for ProtocolStreamProcessor.process_chunk()."""

    def test_process_chunk_auto_detects_adapter(self) -> None:
        """Test that process_chunk auto-detects adapter on first call."""
        registry = Registry(syntax=DelimiterPreambleSyntax())
        processor = ProtocolStreamProcessor(registry)

        # Process a plain string (will auto-detect IdentityInputAdapter)
        processor.process_chunk("hello")

        assert processor.was_auto_detected is True
        assert processor.input_adapter is not None

    def test_process_chunk_text_content(self) -> None:
        """Test processing TEXT_CONTENT events."""
        registry = Registry(syntax=DelimiterPreambleSyntax())
        input_adapter = MockInputAdapter(
            category=EventCategory.TEXT_CONTENT,
            text="Hello world\n",
        )
        output_adapter = StreamBlocksOutputAdapter()

        processor = ProtocolStreamProcessor(
            registry,
            input_adapter=input_adapter,
            output_adapter=output_adapter,
        )

        events = processor.process_chunk({"data": "test"})

        # Should have generated some events
        assert isinstance(events, list)

    def test_process_chunk_passthrough(self) -> None:
        """Test processing PASSTHROUGH events."""
        registry = Registry(syntax=DelimiterPreambleSyntax())
        input_adapter = MockInputAdapter(category=EventCategory.PASSTHROUGH)
        output_adapter = MockOutputAdapter(passthrough_output={"passed": True})

        processor = ProtocolStreamProcessor(
            registry,
            input_adapter=input_adapter,
            output_adapter=output_adapter,
        )

        events = processor.process_chunk({"data": "test"})

        assert len(events) == 1
        assert events[0] == {"passed": True}

    def test_process_chunk_passthrough_returns_none(self) -> None:
        """Test PASSTHROUGH when output adapter returns None."""
        registry = Registry(syntax=DelimiterPreambleSyntax())
        input_adapter = MockInputAdapter(category=EventCategory.PASSTHROUGH)
        output_adapter = MockOutputAdapter(passthrough_output=None)

        processor = ProtocolStreamProcessor(
            registry,
            input_adapter=input_adapter,
            output_adapter=output_adapter,
        )

        events = processor.process_chunk({"data": "test"})

        assert events == []

    def test_process_chunk_skip(self) -> None:
        """Test processing SKIP events."""
        registry = Registry(syntax=DelimiterPreambleSyntax())
        input_adapter = MockInputAdapter(category=EventCategory.SKIP)
        output_adapter = StreamBlocksOutputAdapter()

        processor = ProtocolStreamProcessor(
            registry,
            input_adapter=input_adapter,
            output_adapter=output_adapter,
        )

        events = processor.process_chunk({"data": "test"})

        assert events == []

    def test_process_chunk_with_no_text(self) -> None:
        """Test TEXT_CONTENT with no text extracted."""
        registry = Registry(syntax=DelimiterPreambleSyntax())
        input_adapter = MockInputAdapter(
            category=EventCategory.TEXT_CONTENT,
            text=None,
        )
        output_adapter = StreamBlocksOutputAdapter()

        processor = ProtocolStreamProcessor(
            registry,
            input_adapter=input_adapter,
            output_adapter=output_adapter,
        )

        events = processor.process_chunk({"data": "test"})

        assert events == []

    def test_process_chunk_output_list(self) -> None:
        """Test process_chunk when output adapter returns list."""
        registry = Registry(syntax=DelimiterPreambleSyntax())
        input_adapter = MockInputAdapter(
            category=EventCategory.TEXT_CONTENT,
            text="Hello\n",
        )
        output_adapter = MockOutputAdapter(output=[{"event": 1}, {"event": 2}])

        processor = ProtocolStreamProcessor(
            registry,
            input_adapter=input_adapter,
            output_adapter=output_adapter,
        )

        events = processor.process_chunk({"data": "test"})

        # Should flatten the list
        assert len(events) >= 2

    def test_process_chunk_output_adapter_returns_none(self) -> None:
        """Test process_chunk when output adapter returns None for all events."""
        registry = Registry(syntax=DelimiterPreambleSyntax())
        input_adapter = MockInputAdapter(
            category=EventCategory.TEXT_CONTENT,
            text="Hello\n",
        )
        output_adapter = NoneOutputAdapter()

        processor = ProtocolStreamProcessor(
            registry,
            input_adapter=input_adapter,
            output_adapter=output_adapter,
        )

        # Events are generated but adapter returns None for all
        events = processor.process_chunk({"data": "test"})

        assert events == []


class TestProtocolStreamProcessorFinalize:
    """Tests for ProtocolStreamProcessor.finalize()."""

    def test_finalize_empty(self) -> None:
        """Test finalize with no pending blocks."""
        registry = Registry(syntax=DelimiterPreambleSyntax())
        processor = ProtocolStreamProcessor(registry)

        events = processor.finalize()

        assert isinstance(events, list)

    def test_finalize_flushes_incomplete_blocks(self) -> None:
        """Test finalize flushes incomplete blocks."""
        registry = Registry(syntax=DelimiterPreambleSyntax())
        input_adapter = IdentityInputAdapter()
        output_adapter = StreamBlocksOutputAdapter()

        processor = ProtocolStreamProcessor(
            registry,
            input_adapter=input_adapter,
            output_adapter=output_adapter,
        )

        # Start a block without closing it - use correct syntax format
        processor.process_chunk("!!myblock:file\n")
        processor.process_chunk("content here\n")

        # Finalize should emit rejection event
        events = processor.finalize()

        assert isinstance(events, list)

    def test_finalize_output_adapter_returns_none(self) -> None:
        """Test finalize when output adapter returns None for all events."""
        registry = Registry(syntax=DelimiterPreambleSyntax())
        input_adapter = IdentityInputAdapter()
        output_adapter = NoneOutputAdapter()

        processor = ProtocolStreamProcessor(
            registry,
            input_adapter=input_adapter,
            output_adapter=output_adapter,
        )

        # Open a block without closing it - finalize will emit rejection event
        processor.process_chunk("!!myblock:file\n")
        processor.process_chunk("content\n")
        events = processor.finalize()

        # NoneOutputAdapter returns None, so events list is empty
        assert events == []


class TestProtocolStreamProcessorReset:
    """Tests for ProtocolStreamProcessor.reset()."""

    def test_reset_clears_auto_detected_adapter(self) -> None:
        """Test reset clears auto-detected adapter."""
        registry = Registry(syntax=DelimiterPreambleSyntax())
        processor = ProtocolStreamProcessor(registry)

        # Trigger auto-detection
        processor.process_chunk("hello")
        assert processor.was_auto_detected is True
        assert processor.input_adapter is not None

        # Reset
        processor.reset()

        assert processor.was_auto_detected is False
        assert processor.input_adapter is None

    def test_reset_recreates_core_processor(self) -> None:
        """Test reset recreates core processor."""
        registry = Registry(syntax=DelimiterPreambleSyntax())
        processor = ProtocolStreamProcessor(registry)

        original_core = processor._core_processor

        processor.reset()

        assert processor._core_processor is not original_core


class TestProtocolStreamProcessorProcessStream:
    """Tests for ProtocolStreamProcessor.process_stream()."""

    @pytest.mark.asyncio
    async def test_process_stream_empty(self) -> None:
        """Test processing empty stream."""
        registry = Registry(syntax=DelimiterPreambleSyntax())
        processor = ProtocolStreamProcessor(registry)

        async def empty_stream() -> Any:
            return
            yield  # Make it an async generator

        events: list[Any] = []
        async for event in processor.process_stream(empty_stream()):
            events.append(event)

        assert isinstance(events, list)

    @pytest.mark.asyncio
    async def test_process_stream_text_content(self) -> None:
        """Test processing stream with text content."""
        registry = Registry(syntax=DelimiterPreambleSyntax())
        input_adapter = IdentityInputAdapter()
        config = ProcessorConfig(emit_text_deltas=True)

        processor = ProtocolStreamProcessor(
            registry,
            input_adapter=input_adapter,
            config=config,
        )

        async def text_stream() -> Any:
            yield "Hello "
            yield "world!\n"

        events: list[Any] = []
        async for event in processor.process_stream(text_stream()):
            events.append(event)

        # Should have generated text events
        assert len(events) > 0
        # Should include text delta events
        assert any(isinstance(e, (TextDeltaEvent, TextContentEvent)) for e in events)

    @pytest.mark.asyncio
    async def test_process_stream_auto_detects_adapter(self) -> None:
        """Test that process_stream auto-detects adapter."""
        registry = Registry(syntax=DelimiterPreambleSyntax())
        processor = ProtocolStreamProcessor(registry)

        async def text_stream() -> Any:
            yield "hello"

        async for _ in processor.process_stream(text_stream()):
            pass

        assert processor.was_auto_detected is True
        assert processor.input_adapter is not None

    @pytest.mark.asyncio
    async def test_process_stream_with_block(self) -> None:
        """Test processing stream containing a block."""
        registry = Registry(syntax=DelimiterPreambleSyntax())
        input_adapter = IdentityInputAdapter()

        processor = ProtocolStreamProcessor(
            registry,
            input_adapter=input_adapter,
        )

        # Use correct syntax format: !!<id>:<type> ... !!end
        async def block_stream() -> Any:
            yield "!!myblock:file\n"
            yield "print('hello')\n"
            yield "!!end\n"

        events: list[Any] = []
        async for event in processor.process_stream(block_stream()):
            events.append(event)

        # Should have block start and end events
        assert len(events) > 0
        assert any(isinstance(e, BlockStartEvent) for e in events)
        assert any(isinstance(e, BlockEndEvent) for e in events)

    @pytest.mark.asyncio
    async def test_process_stream_passthrough_events(self) -> None:
        """Test processing stream with passthrough events."""
        registry = Registry(syntax=DelimiterPreambleSyntax())
        input_adapter = MockInputAdapter(category=EventCategory.PASSTHROUGH)
        output_adapter = MockOutputAdapter(passthrough_output={"passed": True})

        processor = ProtocolStreamProcessor(
            registry,
            input_adapter=input_adapter,
            output_adapter=output_adapter,
        )

        async def event_stream() -> Any:
            yield {"event": 1}
            yield {"event": 2}

        events: list[Any] = []
        async for event in processor.process_stream(event_stream()):
            events.append(event)

        assert len(events) == 2
        assert all(e == {"passed": True} for e in events)

    @pytest.mark.asyncio
    async def test_process_stream_skip_events(self) -> None:
        """Test processing stream with skip events."""
        registry = Registry(syntax=DelimiterPreambleSyntax())
        input_adapter = MockInputAdapter(category=EventCategory.SKIP)

        processor = ProtocolStreamProcessor(
            registry,
            input_adapter=input_adapter,
        )

        async def event_stream() -> Any:
            yield {"event": 1}
            yield {"event": 2}

        events: list[Any] = []
        async for event in processor.process_stream(event_stream()):
            events.append(event)

        assert events == []

    @pytest.mark.asyncio
    async def test_process_stream_mixed_events(self) -> None:
        """Test processing stream with mixed event categories."""
        registry = Registry(syntax=DelimiterPreambleSyntax())

        # Create adapter that alternates categories
        class AlternatingAdapter:
            def __init__(self) -> None:
                self._call_count = 0

            def categorize(self, event: Any) -> EventCategory:
                self._call_count += 1
                if self._call_count % 3 == 1:
                    return EventCategory.TEXT_CONTENT
                if self._call_count % 3 == 2:
                    return EventCategory.PASSTHROUGH
                return EventCategory.SKIP

            def extract_text(self, event: Any) -> str | None:
                return "text\n"

            def get_metadata(self, event: Any) -> dict[str, Any] | None:
                return None

            def is_complete(self, event: Any) -> bool:
                return False

        input_adapter = AlternatingAdapter()
        output_adapter = MockOutputAdapter(passthrough_output={"passed": True})

        processor = ProtocolStreamProcessor(
            registry,
            input_adapter=input_adapter,
            output_adapter=output_adapter,
        )

        async def event_stream() -> Any:
            yield {"event": 1}  # TEXT_CONTENT
            yield {"event": 2}  # PASSTHROUGH
            yield {"event": 3}  # SKIP
            yield {"event": 4}  # TEXT_CONTENT
            yield {"event": 5}  # PASSTHROUGH
            yield {"event": 6}  # SKIP

        events: list[Any] = []
        async for event in processor.process_stream(event_stream()):
            events.append(event)

        # Should have events from TEXT_CONTENT and PASSTHROUGH, not SKIP
        assert len(events) > 0

    @pytest.mark.asyncio
    async def test_process_stream_passthrough_returns_none(self) -> None:
        """Test PASSTHROUGH when output adapter returns None."""
        registry = Registry(syntax=DelimiterPreambleSyntax())
        input_adapter = MockInputAdapter(category=EventCategory.PASSTHROUGH)
        # StreamBlocksOutputAdapter returns None for passthrough
        output_adapter = StreamBlocksOutputAdapter()

        processor = ProtocolStreamProcessor(
            registry,
            input_adapter=input_adapter,
            output_adapter=output_adapter,
        )

        async def event_stream() -> Any:
            yield {"event": 1}

        events: list[Any] = []
        async for event in processor.process_stream(event_stream()):
            events.append(event)

        # No events because passthrough returns None
        assert events == []

    @pytest.mark.asyncio
    async def test_process_stream_text_content_empty_text(self) -> None:
        """Test TEXT_CONTENT when extract_text returns None."""
        registry = Registry(syntax=DelimiterPreambleSyntax())
        input_adapter = MockInputAdapter(
            category=EventCategory.TEXT_CONTENT,
            text=None,
        )

        processor = ProtocolStreamProcessor(
            registry,
            input_adapter=input_adapter,
        )

        async def event_stream() -> Any:
            yield {"event": 1}

        events: list[Any] = []
        async for event in processor.process_stream(event_stream()):
            events.append(event)

        # No events because no text to process
        assert events == []

    @pytest.mark.asyncio
    async def test_process_stream_output_adapter_returns_none(self) -> None:
        """Test when output adapter returns None for to_protocol_event."""
        registry = Registry(syntax=DelimiterPreambleSyntax())
        input_adapter = IdentityInputAdapter()
        output_adapter = NoneOutputAdapter()

        processor = ProtocolStreamProcessor(
            registry,
            input_adapter=input_adapter,
            output_adapter=output_adapter,
        )

        async def text_stream() -> Any:
            yield "Hello\n"

        events: list[Any] = []
        async for event in processor.process_stream(text_stream()):
            events.append(event)

        # No events because adapter returns None
        assert events == []


class TestProtocolStreamProcessorEnsureMethods:
    """Tests for ProtocolStreamProcessor helper methods."""

    def test_ensure_list_with_single_item(self) -> None:
        """Test _ensure_list with single item."""
        registry = Registry(syntax=DelimiterPreambleSyntax())
        processor = ProtocolStreamProcessor(registry)

        result = processor._ensure_list({"event": 1})

        assert result == [{"event": 1}]

    def test_ensure_list_with_list(self) -> None:
        """Test _ensure_list with list."""
        registry = Registry(syntax=DelimiterPreambleSyntax())
        processor = ProtocolStreamProcessor(registry)

        items = [{"event": 1}, {"event": 2}]
        result = processor._ensure_list(items)

        assert result is items

    @pytest.mark.asyncio
    async def test_ensure_async_iterable_with_single_item(self) -> None:
        """Test _ensure_async_iterable with single item."""
        registry = Registry(syntax=DelimiterPreambleSyntax())
        processor = ProtocolStreamProcessor(registry)

        items: list[Any] = []
        async for item in processor._ensure_async_iterable({"event": 1}):
            items.append(item)

        assert items == [{"event": 1}]

    @pytest.mark.asyncio
    async def test_ensure_async_iterable_with_list(self) -> None:
        """Test _ensure_async_iterable with list."""
        registry = Registry(syntax=DelimiterPreambleSyntax())
        processor = ProtocolStreamProcessor(registry)

        items: list[Any] = []
        async for item in processor._ensure_async_iterable([{"event": 1}, {"event": 2}]):
            items.append(item)

        assert items == [{"event": 1}, {"event": 2}]


class TestProtocolStreamProcessorIntegration:
    """Integration tests for ProtocolStreamProcessor."""

    @pytest.mark.asyncio
    async def test_full_block_extraction_flow(self) -> None:
        """Test full flow of extracting a block from stream."""
        registry = Registry(syntax=DelimiterPreambleSyntax())
        input_adapter = IdentityInputAdapter()

        processor = ProtocolStreamProcessor(
            registry,
            input_adapter=input_adapter,
        )

        # Use correct syntax format: !!<id>:<type> ... !!end
        async def block_stream() -> Any:
            yield "Some text before\n"
            yield "!!example:file\n"
            yield "def hello():\n"
            yield "    print('Hello')\n"
            yield "!!end\n"
            yield "Some text after\n"

        events: list[Any] = []
        async for event in processor.process_stream(block_stream()):
            events.append(event)

        # Verify we got block events
        block_starts = [e for e in events if isinstance(e, BlockStartEvent)]
        block_ends = [e for e in events if isinstance(e, BlockEndEvent)]

        assert len(block_starts) == 1
        assert len(block_ends) == 1

        # Verify block content (BlockEndEvent has metadata/content as dicts)
        # block_id is a UUID for event tracking, metadata['id'] is the syntax id
        block_end = block_ends[0]
        assert block_end.block_type == "file"
        assert block_end.metadata["block_type"] == "file"
        assert block_end.metadata["id"] == "example"

    @pytest.mark.asyncio
    async def test_sync_and_async_equivalence(self) -> None:
        """Test that sync and async processing yield equivalent results."""
        registry = Registry(syntax=DelimiterPreambleSyntax())
        input_adapter = IdentityInputAdapter()

        # Async processing
        async_processor = ProtocolStreamProcessor(
            registry,
            input_adapter=input_adapter,
        )

        async def text_stream() -> Any:
            yield "Hello\n"
            yield "World\n"

        async_events: list[Any] = []
        async for event in async_processor.process_stream(text_stream()):
            async_events.append(event)
        async_events.extend(async_processor.finalize())

        # Sync processing
        sync_processor = ProtocolStreamProcessor(
            registry,
            input_adapter=input_adapter,
        )

        sync_events: list[Any] = []
        sync_events.extend(sync_processor.process_chunk("Hello\n"))
        sync_events.extend(sync_processor.process_chunk("World\n"))
        sync_events.extend(sync_processor.finalize())

        # Both should produce events of the same types
        async_types = {type(e).__name__ for e in async_events}
        sync_types = {type(e).__name__ for e in sync_events}

        assert async_types == sync_types
