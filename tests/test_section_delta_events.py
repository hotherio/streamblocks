"""Tests for section-specific delta events.

These tests verify that BlockHeaderDeltaEvent, BlockMetadataDeltaEvent,
and BlockContentDeltaEvent are emitted correctly during stream processing.
"""

from typing import Any

import pytest

from hother.streamblocks import (
    BlockContentDeltaEvent,
    BlockEndEvent,
    BlockHeaderDeltaEvent,
    BlockMetadataDeltaEvent,
    BlockStartEvent,
    DelimiterFrontmatterSyntax,
    EventType,
    Registry,
    StreamBlockProcessor,
)


@pytest.mark.asyncio
async def test_section_delta_events_emitted() -> None:
    """Test that section-specific delta events are emitted during processing."""
    syntax = DelimiterFrontmatterSyntax()
    registry = Registry(syntax=syntax)
    from hother.streamblocks.core.processor import ProcessorConfig

    config = ProcessorConfig(emit_text_deltas=False)
    processor = StreamBlockProcessor(registry, config=config)

    async def mock_stream() -> Any:
        text = """Some text before.

!!start
---
id: test-block
block_type: generic
---
This is content line 1.
This is content line 2.
!!end

Some text after."""
        for line in text.split("\n"):
            yield line + "\n"

    header_deltas: list[BlockHeaderDeltaEvent] = []
    metadata_deltas: list[BlockMetadataDeltaEvent] = []
    content_deltas: list[BlockContentDeltaEvent] = []
    start_events: list[BlockStartEvent] = []
    end_events: list[BlockEndEvent] = []

    async for event in processor.process_stream(mock_stream()):
        if event.type == EventType.BLOCK_START:
            assert isinstance(event, BlockStartEvent)
            start_events.append(event)
        elif event.type == EventType.BLOCK_HEADER_DELTA:
            assert isinstance(event, BlockHeaderDeltaEvent)
            header_deltas.append(event)
        elif event.type == EventType.BLOCK_METADATA_DELTA:
            assert isinstance(event, BlockMetadataDeltaEvent)
            metadata_deltas.append(event)
        elif event.type == EventType.BLOCK_CONTENT_DELTA:
            assert isinstance(event, BlockContentDeltaEvent)
            content_deltas.append(event)
        elif event.type == EventType.BLOCK_END:
            assert isinstance(event, BlockEndEvent)
            end_events.append(event)

    # Verify we got one block
    assert len(start_events) == 1
    assert len(end_events) == 1

    # Verify section-specific events were emitted
    # Metadata section (YAML frontmatter lines: ---, id: ..., block_type: ..., ---)
    assert len(metadata_deltas) >= 3, f"Expected at least 3 metadata deltas, got {len(metadata_deltas)}"

    # Content section (content lines)
    assert len(content_deltas) >= 2, f"Expected at least 2 content deltas, got {len(content_deltas)}"

    # Verify content deltas have correct content
    content_texts = [e.delta for e in content_deltas]
    assert any("content line 1" in text for text in content_texts)
    assert any("content line 2" in text for text in content_texts)


@pytest.mark.asyncio
async def test_metadata_boundary_flag() -> None:
    """Test that is_boundary flag is set on metadata boundary lines."""
    syntax = DelimiterFrontmatterSyntax()
    registry = Registry(syntax=syntax)
    from hother.streamblocks.core.processor import ProcessorConfig

    config = ProcessorConfig(emit_text_deltas=False)
    processor = StreamBlockProcessor(registry, config=config)

    async def mock_stream() -> Any:
        text = """!!start
---
id: test-block
block_type: generic
---
Content here.
!!end"""
        for line in text.split("\n"):
            yield line + "\n"

    metadata_deltas: list[BlockMetadataDeltaEvent] = []

    async for event in processor.process_stream(mock_stream()):
        if event.type == EventType.BLOCK_METADATA_DELTA:
            assert isinstance(event, BlockMetadataDeltaEvent)
            metadata_deltas.append(event)

    # Check that boundary events exist (at least the --- markers)
    boundary_events = [e for e in metadata_deltas if e.is_boundary]
    # The closing --- should trigger a boundary event
    assert len(boundary_events) >= 1, "Expected at least one boundary event for ---"


@pytest.mark.asyncio
async def test_block_start_event_fields() -> None:
    """Test that BlockStartEvent has correct fields."""
    syntax = DelimiterFrontmatterSyntax()
    registry = Registry(syntax=syntax)
    from hother.streamblocks.core.processor import ProcessorConfig

    config = ProcessorConfig(emit_text_deltas=False)
    processor = StreamBlockProcessor(registry, config=config)

    async def mock_stream() -> Any:
        text = """!!start
---
id: my-block
block_type: test
---
Content.
!!end"""
        for line in text.split("\n"):
            yield line + "\n"

    start_events: list[BlockStartEvent] = []

    async for event in processor.process_stream(mock_stream()):
        if event.type == EventType.BLOCK_START:
            assert isinstance(event, BlockStartEvent)
            start_events.append(event)

    assert len(start_events) == 1
    start_event = start_events[0]

    # Verify BlockStartEvent fields
    assert start_event.block_id is not None
    assert start_event.syntax == "DelimiterFrontmatterSyntax"
    assert start_event.start_line == 1
    # block_type may be None until parsed
    assert start_event.block_type is None


@pytest.mark.asyncio
async def test_delta_events_have_correct_block_id() -> None:
    """Test that all delta events share the same block_id."""
    syntax = DelimiterFrontmatterSyntax()
    registry = Registry(syntax=syntax)
    from hother.streamblocks.core.processor import ProcessorConfig

    config = ProcessorConfig(emit_text_deltas=False)
    processor = StreamBlockProcessor(registry, config=config)

    async def mock_stream() -> Any:
        text = """!!start
---
id: test
block_type: generic
---
Content.
!!end"""
        for line in text.split("\n"):
            yield line + "\n"

    block_ids: set[str] = set()

    async for event in processor.process_stream(mock_stream()):
        if event.type == EventType.BLOCK_START:
            assert isinstance(event, BlockStartEvent)
            block_ids.add(event.block_id)
        elif event.type == EventType.BLOCK_HEADER_DELTA:
            assert isinstance(event, BlockHeaderDeltaEvent)
            block_ids.add(event.block_id)
        elif event.type == EventType.BLOCK_METADATA_DELTA:
            assert isinstance(event, BlockMetadataDeltaEvent)
            block_ids.add(event.block_id)
        elif event.type == EventType.BLOCK_CONTENT_DELTA:
            assert isinstance(event, BlockContentDeltaEvent)
            block_ids.add(event.block_id)
        elif event.type == EventType.BLOCK_END:
            assert isinstance(event, BlockEndEvent)
            block_ids.add(event.block_id)

    # All events for a single block should have the same block_id
    assert len(block_ids) == 1, f"Expected 1 block_id, got {len(block_ids)}: {block_ids}"


@pytest.mark.asyncio
async def test_delta_events_have_accumulated_size() -> None:
    """Test that delta events track accumulated_size correctly."""
    syntax = DelimiterFrontmatterSyntax()
    registry = Registry(syntax=syntax)
    from hother.streamblocks.core.processor import ProcessorConfig

    config = ProcessorConfig(emit_text_deltas=False)
    processor = StreamBlockProcessor(registry, config=config)

    async def mock_stream() -> Any:
        text = """!!start
---
id: test
block_type: generic
---
Line 1.
Line 2.
!!end"""
        for line in text.split("\n"):
            yield line + "\n"

    accumulated_sizes: list[int] = []

    async for event in processor.process_stream(mock_stream()):
        if isinstance(event, BlockMetadataDeltaEvent | BlockContentDeltaEvent):
            accumulated_sizes.append(event.accumulated_size)

    # Accumulated size should increase with each line
    for i in range(1, len(accumulated_sizes)):
        assert accumulated_sizes[i] >= accumulated_sizes[i - 1], (
            f"accumulated_size should not decrease: {accumulated_sizes}"
        )


@pytest.mark.asyncio
async def test_delta_events_have_current_line() -> None:
    """Test that delta events have current_line field."""
    syntax = DelimiterFrontmatterSyntax()
    registry = Registry(syntax=syntax)
    from hother.streamblocks.core.processor import ProcessorConfig

    config = ProcessorConfig(emit_text_deltas=False)
    processor = StreamBlockProcessor(registry, config=config)

    async def mock_stream() -> Any:
        text = """!!start
---
id: test
block_type: generic
---
Content.
!!end"""
        for line in text.split("\n"):
            yield line + "\n"

    current_lines: list[int] = []

    async for event in processor.process_stream(mock_stream()):
        if isinstance(event, BlockMetadataDeltaEvent | BlockContentDeltaEvent):
            current_lines.append(event.current_line)

    # current_line should increase
    for i in range(1, len(current_lines)):
        assert current_lines[i] >= current_lines[i - 1], f"current_line should increase: {current_lines}"


@pytest.mark.asyncio
async def test_delta_events_have_syntax_field() -> None:
    """Test that all delta events have the syntax field."""
    syntax = DelimiterFrontmatterSyntax()
    registry = Registry(syntax=syntax)
    from hother.streamblocks.core.processor import ProcessorConfig

    config = ProcessorConfig(emit_text_deltas=False)
    processor = StreamBlockProcessor(registry, config=config)

    async def mock_stream() -> Any:
        text = """!!start
---
id: test
block_type: generic
---
Content.
!!end"""
        for line in text.split("\n"):
            yield line + "\n"

    async for event in processor.process_stream(mock_stream()):
        if isinstance(event, BlockHeaderDeltaEvent | BlockMetadataDeltaEvent | BlockContentDeltaEvent):
            assert event.syntax == "DelimiterFrontmatterSyntax"
