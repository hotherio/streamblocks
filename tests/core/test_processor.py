"""Tests for core processor module."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from hother.streamblocks import Registry
from hother.streamblocks.adapters.input import IdentityInputAdapter
from hother.streamblocks.adapters.protocols import InputProtocolAdapter
from hother.streamblocks.core.processor import (
    ProcessorConfig,
    StreamBlockProcessor,
    StreamState,
)
from hother.streamblocks.core.types import (
    BlockEndEvent,
    BlockErrorEvent,
    TextDeltaEvent,
)
from hother.streamblocks.core.utils import get_syntax_name
from hother.streamblocks.syntaxes.delimiter import DelimiterPreambleSyntax


@pytest.fixture
def syntax() -> DelimiterPreambleSyntax:
    """Create a default syntax for tests."""
    return DelimiterPreambleSyntax()


@pytest.fixture
def registry(syntax: DelimiterPreambleSyntax) -> Registry:
    """Create a registry with the default syntax."""
    return Registry(syntax=syntax)


class TestStreamState:
    """Tests for StreamState dataclass."""

    def test_stream_state_default_values(self) -> None:
        """Test StreamState has correct default values."""
        state = StreamState()

        assert state.stream_id is not None
        assert state.start_time > 0
        assert state.blocks_extracted == 0
        assert state.blocks_rejected == 0
        assert state.total_events == 0

    def test_duration_ms_returns_elapsed_time(self) -> None:
        """Test duration_ms returns elapsed time.

        This covers line 45.
        """
        state = StreamState()
        # Wait a small amount
        time.sleep(0.01)  # 10ms

        duration = state.duration_ms()

        # Should be at least 10ms (allow some margin)
        assert duration >= 5


class TestProcessorConfig:
    """Tests for ProcessorConfig dataclass."""

    def test_default_config_values(self) -> None:
        """Test ProcessorConfig default values."""
        config = ProcessorConfig()

        assert config.lines_buffer == 5
        assert config.max_line_length == 16_384
        assert config.max_block_size == 1_048_576
        assert config.emit_original_events is True
        assert config.emit_text_deltas is True
        assert config.emit_section_end_events is True
        assert config.auto_detect_adapter is True

    def test_custom_config_values(self) -> None:
        """Test ProcessorConfig with custom values."""
        config = ProcessorConfig(
            lines_buffer=10,
            emit_original_events=False,
            auto_detect_adapter=False,
        )

        assert config.lines_buffer == 10
        assert config.emit_original_events is False
        assert config.auto_detect_adapter is False


class TestGetSyntaxName:
    """Tests for get_syntax_name function."""

    def testget_syntax_name_returns_class_name(self) -> None:
        """Test that get_syntax_name returns the class name."""
        syntax = DelimiterPreambleSyntax()

        name = get_syntax_name(syntax)

        assert name == "DelimiterPreambleSyntax"


class TestStreamBlockProcessorInit:
    """Tests for StreamBlockProcessor initialization."""

    def test_processor_initialization(self, registry: Registry) -> None:
        """Test basic processor initialization."""
        processor = StreamBlockProcessor(registry)

        assert processor.registry is registry
        assert processor.syntax is registry.syntax
        assert processor.config is not None

    def test_processor_with_custom_config(self, registry: Registry) -> None:
        """Test processor with custom configuration."""
        config = ProcessorConfig(emit_text_deltas=False)

        processor = StreamBlockProcessor(registry, config=config)

        assert processor.config.emit_text_deltas is False

    def test_processor_with_custom_logger(self, registry: Registry) -> None:
        """Test processor with custom logger."""
        mock_logger = MagicMock()

        processor = StreamBlockProcessor(registry, logger=mock_logger)

        assert processor.logger is mock_logger


class TestStreamBlockProcessorProcessChunk:
    """Tests for StreamBlockProcessor.process_chunk()."""

    def test_process_chunk_with_text(self, registry: Registry) -> None:
        """Test processing a simple text chunk."""
        processor = StreamBlockProcessor(registry)

        events = processor.process_chunk("Hello, world!")

        # Should have text delta event
        text_deltas = [e for e in events if isinstance(e, TextDeltaEvent)]
        assert len(text_deltas) == 1
        assert text_deltas[0].delta == "Hello, world!"

    def test_process_chunk_emit_original_events_with_non_identity_adapter(self, registry: Registry) -> None:
        """Test that original chunks are emitted with non-identity adapter.

        This covers line 170.
        """
        config = ProcessorConfig(emit_original_events=True)
        processor = StreamBlockProcessor(registry, config=config)

        # Create a mock adapter that is NOT an IdentityInputAdapter
        mock_adapter = MagicMock(spec=InputProtocolAdapter)
        mock_adapter.extract_text = MagicMock(return_value="text")

        # Provide the adapter explicitly
        chunk = {"content": "test"}
        events = processor.process_chunk(chunk, adapter=mock_adapter)

        # The original chunk should be in the events
        assert chunk in events

    def test_process_chunk_no_original_events_with_identity_adapter(self, registry: Registry) -> None:
        """Test that original chunks are NOT emitted with IdentityInputAdapter."""
        config = ProcessorConfig(emit_original_events=True)
        processor = StreamBlockProcessor(registry, config=config)

        # Use string chunks which use IdentityInputAdapter
        events = processor.process_chunk("text")

        # The original string should NOT be in events (only events are)
        non_event_items = [e for e in events if isinstance(e, str)]
        assert len(non_event_items) == 0

    def test_process_chunk_returns_empty_when_no_text(self, registry: Registry) -> None:
        """Test that processing empty text returns only passthrough event.

        This covers line 179.
        """
        processor = StreamBlockProcessor(registry)

        # Create adapter that returns empty string
        mock_adapter = MagicMock(spec=InputProtocolAdapter)
        mock_adapter.extract_text = MagicMock(return_value="")

        events = processor.process_chunk({}, adapter=mock_adapter)

        # Should only have the original chunk (passthrough), no TextDeltaEvent
        text_deltas = [e for e in events if isinstance(e, TextDeltaEvent)]
        assert len(text_deltas) == 0

    def test_process_chunk_raises_if_adapter_not_set(self, registry: Registry) -> None:
        """Test RuntimeError if adapter is None after first chunk.

        This covers lines 174-175.
        """
        config = ProcessorConfig(auto_detect_adapter=False)
        processor = StreamBlockProcessor(registry, config=config)

        # Manually break the invariant by setting _first_chunk_processed
        # without setting _adapter
        processor._first_chunk_processed = True
        processor._adapter = None

        with pytest.raises(RuntimeError, match="Adapter should be set"):
            processor.process_chunk("text")


class TestStreamBlockProcessorFinalize:
    """Tests for StreamBlockProcessor.finalize()."""

    def test_finalize_processes_remaining_text(self, registry: Registry) -> None:
        """Test that finalize processes remaining text."""
        processor = StreamBlockProcessor(registry)

        # Process chunk without newline
        processor.process_chunk("partial line")

        # Finalize should process the remaining text
        events = processor.finalize()

        assert isinstance(events, list)

    def test_finalize_flushes_incomplete_blocks(self, registry: Registry) -> None:
        """Test that finalize flushes incomplete blocks."""
        processor = StreamBlockProcessor(registry)

        # Start a block but don't close it
        processor.process_chunk("!!myblock:test\n")
        processor.process_chunk("content\n")

        # Finalize should create error events for incomplete blocks
        events = processor.finalize()

        error_events = [e for e in events if isinstance(e, BlockErrorEvent)]
        assert len(error_events) > 0


class TestStreamBlockProcessorIsNativeEvent:
    """Tests for StreamBlockProcessor.is_native_event()."""

    def test_is_native_event_returns_false_for_streamblocks_events(self, registry: Registry) -> None:
        """Test is_native_event returns False for StreamBlocks events.

        This covers lines 270-287.
        """
        processor = StreamBlockProcessor(registry)

        # Test various StreamBlocks events
        assert processor.is_native_event(TextDeltaEvent(delta="text")) is False
        assert (
            processor.is_native_event(
                BlockEndEvent(
                    block_id="1",
                    block_type="test",
                    syntax="TestSyntax",
                    start_line=1,
                    end_line=10,
                    metadata={"id": "1", "block_type": "test"},
                    content={"raw_content": "content"},
                    raw_content="content",
                    hash_id="abc123",
                )
            )
            is False
        )
        assert (
            processor.is_native_event(BlockErrorEvent(block_id="1", reason="test", syntax="TestSyntax", start_line=1))
            is False
        )

    def test_is_native_event_returns_false_when_no_adapter(self, registry: Registry) -> None:
        """Test is_native_event returns False when no adapter set.

        This covers lines 290-291.
        """
        processor = StreamBlockProcessor(registry)

        # Don't set adapter
        processor._adapter = None

        result = processor.is_native_event({"some": "event"})

        assert result is False

    def test_is_native_event_returns_false_when_no_module_prefix(self, registry: Registry) -> None:
        """Test is_native_event returns False when adapter has no module prefix.

        This covers lines 293-295.
        """
        processor = StreamBlockProcessor(registry)

        # Set adapter without native_module_prefix
        mock_adapter = MagicMock(spec=InputProtocolAdapter)
        if hasattr(mock_adapter, "native_module_prefix"):
            del mock_adapter.native_module_prefix
        processor._adapter = mock_adapter
        processor._first_chunk_processed = True

        result = processor.is_native_event({"some": "event"})

        assert result is False

    def test_is_native_event_returns_true_for_matching_module(self, registry: Registry) -> None:
        """Test is_native_event returns True for matching module.

        This covers lines 297-298.
        """
        processor = StreamBlockProcessor(registry)

        # Set adapter with native_module_prefix
        mock_adapter = MagicMock()
        mock_adapter.native_module_prefix = "unittest.mock"
        processor._adapter = mock_adapter
        processor._first_chunk_processed = True

        # Create an object from unittest.mock module
        mock_event = MagicMock()

        result = processor.is_native_event(mock_event)

        assert result is True

    def test_is_native_event_returns_false_for_non_matching_module(self, registry: Registry) -> None:
        """Test is_native_event returns False for non-matching module."""
        processor = StreamBlockProcessor(registry)

        # Set adapter with a prefix that won't match
        mock_adapter = MagicMock()
        mock_adapter.native_module_prefix = "google.ai"
        processor._adapter = mock_adapter
        processor._first_chunk_processed = True

        # Use a dict (from builtins)
        result = processor.is_native_event({"event": "data"})

        assert result is False


class TestStreamBlockProcessorProcessStream:
    """Tests for StreamBlockProcessor.process_stream()."""

    @pytest.mark.asyncio
    async def test_process_stream_with_explicit_adapter(self, registry: Registry) -> None:
        """Test process_stream with explicitly provided adapter.

        This covers lines 337-338.
        """
        processor = StreamBlockProcessor(registry)

        # Create mock adapter
        mock_adapter = MagicMock(spec=InputProtocolAdapter)
        mock_adapter.extract_text = MagicMock(return_value="text")

        async def mock_stream():
            yield {"chunk": 1}

        events = []
        async for event in processor.process_stream(mock_stream(), adapter=mock_adapter):
            events.append(event)

        assert processor._adapter is mock_adapter

    @pytest.mark.asyncio
    async def test_process_stream_yields_original_chunks(self, registry: Registry) -> None:
        """Test process_stream yields original chunks with non-identity adapter.

        This covers line 346.
        """
        config = ProcessorConfig(emit_original_events=True)
        processor = StreamBlockProcessor(registry, config=config)

        # Create mock adapter
        mock_adapter = MagicMock(spec=InputProtocolAdapter)
        mock_adapter.extract_text = MagicMock(return_value="text")

        async def mock_stream():
            yield {"chunk": 1}
            yield {"chunk": 2}

        chunks = []
        async for event in processor.process_stream(mock_stream(), adapter=mock_adapter):
            if isinstance(event, dict):
                chunks.append(event)

        assert {"chunk": 1} in chunks
        assert {"chunk": 2} in chunks

    @pytest.mark.asyncio
    async def test_process_stream_continues_on_empty_text(self, registry: Registry) -> None:
        """Test process_stream continues when adapter returns empty text.

        This covers line 355.
        """
        processor = StreamBlockProcessor(registry)

        # Create mock adapter that returns empty text for first chunk
        mock_adapter = MagicMock(spec=InputProtocolAdapter)
        mock_adapter.extract_text = MagicMock(side_effect=["", "actual text"])

        async def mock_stream():
            yield {"chunk": 1}  # Will return empty text
            yield {"chunk": 2}  # Will return actual text

        events = []
        async for event in processor.process_stream(mock_stream(), adapter=mock_adapter):
            events.append(event)

        # Should have events from the second chunk
        text_deltas = [e for e in events if isinstance(e, TextDeltaEvent)]
        assert len(text_deltas) == 1
        assert text_deltas[0].delta == "actual text"

    @pytest.mark.asyncio
    async def test_process_stream_raises_if_adapter_not_set(self, registry: Registry) -> None:
        """Test RuntimeError if adapter is None after first chunk.

        This covers lines 350-351.
        """
        config = ProcessorConfig(auto_detect_adapter=False)
        processor = StreamBlockProcessor(registry, config=config)

        # Manually break the invariant
        processor._first_chunk_processed = True
        processor._adapter = None

        async def mock_stream():
            yield "text"

        with pytest.raises(RuntimeError, match="Adapter should be set"):
            async for _event in processor.process_stream(mock_stream()):
                pass


class TestStreamBlockProcessorEnsureAdapter:
    """Tests for StreamBlockProcessor._ensure_adapter()."""

    def test_ensure_adapter_uses_provided_adapter(self, registry: Registry) -> None:
        """Test _ensure_adapter uses provided adapter."""
        processor = StreamBlockProcessor(registry)

        mock_adapter = MagicMock(spec=InputProtocolAdapter)
        processor._ensure_adapter("chunk", mock_adapter)

        assert processor._adapter is mock_adapter
        assert processor._first_chunk_processed is True

    def test_ensure_adapter_auto_detects(self, registry: Registry) -> None:
        """Test _ensure_adapter auto-detects adapter."""
        config = ProcessorConfig(auto_detect_adapter=True)
        processor = StreamBlockProcessor(registry, config=config)

        # String chunks should use IdentityInputAdapter
        processor._ensure_adapter("text", None)

        assert isinstance(processor._adapter, IdentityInputAdapter)

    def test_ensure_adapter_fallback_to_identity_when_detection_fails(self, registry: Registry) -> None:
        """Test _ensure_adapter falls back to IdentityInputAdapter.

        This covers lines 405-406.
        """
        config = ProcessorConfig(auto_detect_adapter=True)
        processor = StreamBlockProcessor(registry, config=config)

        # Use a custom object that won't match any registered adapter
        class UnknownChunk:
            pass

        # Patch detect to return None
        with patch("hother.streamblocks.core.processor.InputAdapterRegistry.detect", return_value=None):
            processor._ensure_adapter(UnknownChunk(), None)

        assert isinstance(processor._adapter, IdentityInputAdapter)

    def test_ensure_adapter_uses_identity_when_auto_detect_disabled(self, registry: Registry) -> None:
        """Test _ensure_adapter uses IdentityInputAdapter when auto-detect disabled.

        This covers line 395 (implicitly) and 408.
        """
        config = ProcessorConfig(auto_detect_adapter=False)
        processor = StreamBlockProcessor(registry, config=config)

        processor._ensure_adapter({"complex": "object"}, None)

        assert isinstance(processor._adapter, IdentityInputAdapter)

    def test_ensure_adapter_skips_if_already_processed(self, registry: Registry) -> None:
        """Test _ensure_adapter does nothing if already processed."""
        processor = StreamBlockProcessor(registry)

        # Mark as already processed
        original_adapter = MagicMock(spec=InputProtocolAdapter)
        processor._adapter = original_adapter
        processor._first_chunk_processed = True

        # Try to ensure with a different adapter
        new_adapter = MagicMock(spec=InputProtocolAdapter)
        processor._ensure_adapter("chunk", new_adapter)

        # Should keep the original adapter
        assert processor._adapter is original_adapter


class TestStreamBlockProcessorIntegration:
    """Integration tests for StreamBlockProcessor."""

    def test_process_complete_block(self, registry: Registry) -> None:
        """Test processing a complete block."""
        processor = StreamBlockProcessor(registry)

        # Process a complete block - closing marker is !!end for DelimiterPreambleSyntax
        events = []
        events.extend(processor.process_chunk("!!myblock:test\n"))
        events.extend(processor.process_chunk("content line\n"))
        events.extend(processor.process_chunk("!!end\n"))
        events.extend(processor.finalize())

        # Should have a BlockEndEvent
        block_ends = [e for e in events if isinstance(e, BlockEndEvent)]
        assert len(block_ends) == 1

    @pytest.mark.asyncio
    async def test_async_process_complete_block(self, registry: Registry) -> None:
        """Test async processing of a complete block."""
        processor = StreamBlockProcessor(registry)

        async def mock_stream():
            yield "!!myblock:test\n"
            yield "content line\n"
            yield "!!end\n"

        events = []
        async for event in processor.process_stream(mock_stream()):
            events.append(event)

        # Should have a BlockEndEvent
        block_ends = [e for e in events if isinstance(e, BlockEndEvent)]
        assert len(block_ends) == 1
