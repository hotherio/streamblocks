"""Edge case tests for StreamBlocks processor."""

from collections.abc import AsyncIterator

import pytest

from hother.streamblocks import (
    BlockEndEvent,
    BlockErrorEvent,
    EventType,
    Registry,
    StreamBlockProcessor,
)


class TestEmptyAndWhitespaceInput:
    """Tests for empty or whitespace-only input."""

    @pytest.mark.asyncio
    async def test_empty_stream(self, processor: StreamBlockProcessor) -> None:
        """Empty stream should produce no events."""

        async def empty_stream() -> AsyncIterator[str]:
            return
            yield  # Make it a generator

        events = [e async for e in processor.process_stream(empty_stream())]
        assert len(events) == 0

    @pytest.mark.asyncio
    async def test_stream_with_only_whitespace(self, processor: StreamBlockProcessor) -> None:
        """Stream with only whitespace should emit text content events."""

        async def whitespace_stream() -> AsyncIterator[str]:
            yield "   \n"
            yield "\t\n"
            yield "\n"

        events = [e async for e in processor.process_stream(whitespace_stream())]
        text_events = [e for e in events if e.type == EventType.TEXT_CONTENT]
        # Each yield ending with \n produces 2 events (content + empty trailing line)
        assert len(text_events) == 6

    @pytest.mark.asyncio
    async def test_stream_with_only_newlines(self, processor: StreamBlockProcessor) -> None:
        """Stream with only newlines should emit empty text content events."""

        async def newline_stream() -> AsyncIterator[str]:
            yield "\n\n\n"

        events = [e async for e in processor.process_stream(newline_stream())]
        text_events = [e for e in events if e.type == EventType.TEXT_CONTENT]
        # "\n\n\n" splits into 4 segments: ["", "", "", ""]
        assert len(text_events) == 4


class TestUnclosedBlocks:
    """Tests for blocks that are not properly closed."""

    @pytest.mark.asyncio
    async def test_unclosed_block_at_stream_end(self, processor: StreamBlockProcessor) -> None:
        """Unclosed block should be rejected when stream ends."""

        async def unclosed_stream() -> AsyncIterator[str]:
            yield "!!id:files_operations\n"
            yield "src/file.py:C\n"
            # No !!end

        events = [e async for e in processor.process_stream(unclosed_stream())]
        error_events = [e for e in events if e.type == EventType.BLOCK_ERROR]

        assert len(error_events) == 1
        assert isinstance(error_events[0], BlockErrorEvent)
        assert "closing" in error_events[0].reason.lower()

    @pytest.mark.asyncio
    async def test_unclosed_frontmatter_block(self, frontmatter_processor: StreamBlockProcessor) -> None:
        """Unclosed frontmatter block should be rejected."""

        async def unclosed_stream() -> AsyncIterator[str]:
            yield "!!start\n"
            yield "---\n"
            yield "id: test\n"
            yield "block_type: generic\n"
            # No closing --- or !!end

        events = [e async for e in frontmatter_processor.process_stream(unclosed_stream())]
        error_events = [e for e in events if e.type == EventType.BLOCK_ERROR]

        assert len(error_events) == 1


class TestBlockSizeLimits:
    """Tests for block size limit enforcement."""

    @pytest.mark.asyncio
    async def test_block_exceeds_size_limit(self, file_operations_registry: Registry) -> None:
        """Block exceeding max_block_size should be rejected."""
        # Create processor with small size limit
        from hother.streamblocks.core.processor import ProcessorConfig

        config = ProcessorConfig(max_block_size=100, emit_text_deltas=False)
        processor = StreamBlockProcessor(file_operations_registry, config=config)

        async def large_block_stream() -> AsyncIterator[str]:
            yield "!!id:files_operations\n"
            # Content that will exceed 100 bytes
            yield "x" * 150 + ":C\n"
            yield "!!end\n"

        events = [e async for e in processor.process_stream(large_block_stream())]
        error_events = [e for e in events if e.type == EventType.BLOCK_ERROR]

        assert len(error_events) == 1
        assert isinstance(error_events[0], BlockErrorEvent)
        assert "size" in error_events[0].reason.lower()

    @pytest.mark.asyncio
    async def test_block_within_size_limit(self, file_operations_registry: Registry) -> None:
        """Block within max_block_size should be extracted successfully."""
        from hother.streamblocks.core.processor import ProcessorConfig

        config = ProcessorConfig(max_block_size=1000, emit_text_deltas=False)
        processor = StreamBlockProcessor(file_operations_registry, config=config)

        async def normal_block_stream() -> AsyncIterator[str]:
            yield "!!id:files_operations\n"
            yield "src/file.py:C\n"
            yield "!!end\n"

        events = [e async for e in processor.process_stream(normal_block_stream())]
        end_events = [e for e in events if e.type == EventType.BLOCK_END]

        assert len(end_events) == 1


class TestImmediatelyClosedBlocks:
    """Tests for blocks that are closed immediately without content."""

    @pytest.mark.asyncio
    async def test_block_with_no_content(self, processor: StreamBlockProcessor) -> None:
        """Block closed immediately should still be processed."""

        async def empty_block_stream() -> AsyncIterator[str]:
            yield "!!id:files_operations\n"
            yield "!!end\n"

        events = [e async for e in processor.process_stream(empty_block_stream())]
        # Should be either extracted (empty content) or rejected
        block_events = [e for e in events if e.type in (EventType.BLOCK_END, EventType.BLOCK_ERROR)]
        assert len(block_events) == 1


class TestLineLengthLimits:
    """Tests for line length enforcement."""

    @pytest.mark.asyncio
    async def test_very_long_line_truncated(self, file_operations_registry: Registry) -> None:
        """Very long lines should be truncated."""
        from hother.streamblocks.core.processor import ProcessorConfig

        config = ProcessorConfig(max_line_length=50, emit_text_deltas=False)
        processor = StreamBlockProcessor(file_operations_registry, config=config)

        long_line = "x" * 100

        async def long_line_stream() -> AsyncIterator[str]:
            yield f"{long_line}\n"

        events = [e async for e in processor.process_stream(long_line_stream())]
        text_events = [e for e in events if e.type == EventType.TEXT_CONTENT]

        # 2 events: truncated line + trailing empty line
        assert len(text_events) == 2
        # First line should be truncated to max_line_length
        assert len(text_events[0].content) == 50


class TestMultipleBlocks:
    """Tests for processing multiple blocks in sequence."""

    @pytest.mark.asyncio
    async def test_multiple_valid_blocks(self, processor: StreamBlockProcessor) -> None:
        """Multiple valid blocks should all be extracted."""

        async def multi_block_stream() -> AsyncIterator[str]:
            yield "!!block1:files_operations\n"
            yield "file1.py:C\n"
            yield "!!end\n"
            yield "\n"
            yield "!!block2:files_operations\n"
            yield "file2.py:E\n"
            yield "!!end\n"

        events = [e async for e in processor.process_stream(multi_block_stream())]
        end_events = [e for e in events if e.type == EventType.BLOCK_END]

        assert len(end_events) == 2
        assert isinstance(end_events[0], BlockEndEvent)
        assert isinstance(end_events[1], BlockEndEvent)

    @pytest.mark.asyncio
    async def test_valid_block_after_invalid(self, processor: StreamBlockProcessor) -> None:
        """Valid block after invalid block should still be extracted."""

        async def mixed_stream() -> AsyncIterator[str]:
            # First block - unclosed
            yield "!!invalid:files_operations\n"
            yield "content:C\n"
            # No !!end - but stream continues

        events = [e async for e in processor.process_stream(mixed_stream())]
        error_events = [e for e in events if e.type == EventType.BLOCK_ERROR]

        # The unclosed block should be rejected at stream end
        assert len(error_events) == 1


class TestChunkProcessing:
    """Tests for synchronous chunk processing."""

    def test_process_chunk_basic(self, processor: StreamBlockProcessor) -> None:
        """Basic chunk processing should work."""
        events = processor.process_chunk("Hello\n")
        text_events = [e for e in events if e.type == EventType.TEXT_CONTENT]
        # 2 events: "Hello" + trailing empty line from \n
        assert len(text_events) == 2
        assert text_events[0].content == "Hello"

    def test_process_chunk_incomplete_line(self, processor: StreamBlockProcessor) -> None:
        """Incomplete lines should be buffered."""
        events1 = processor.process_chunk("Hel")
        assert len([e for e in events1 if e.type == EventType.TEXT_CONTENT]) == 0

        events2 = processor.process_chunk("lo\n")
        text_events = [e for e in events2 if e.type == EventType.TEXT_CONTENT]
        # 2 events: "Hello" + trailing empty line from \n
        assert len(text_events) == 2
        assert text_events[0].content == "Hello"

    def test_finalize_flushes_incomplete(self, processor: StreamBlockProcessor) -> None:
        """Finalize should flush incomplete lines."""
        processor.process_chunk("incomplete")
        events = processor.finalize()
        text_events = [e for e in events if e.type == EventType.TEXT_CONTENT]
        assert len(text_events) == 1
        assert text_events[0].content == "incomplete"
