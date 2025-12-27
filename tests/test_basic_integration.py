"""Basic integration tests for StreamBlocks."""

import asyncio
from typing import Any

import pytest

from hother.streamblocks import (
    BlockEndEvent,
    DelimiterPreambleSyntax,
    EventType,
    Registry,
    StreamBlockProcessor,
)
from hother.streamblocks_examples.blocks.agent import FileOperations


@pytest.mark.asyncio
async def test_basic_delimiter_preamble_syntax() -> None:
    """Test basic functionality with delimiter preamble syntax."""
    # Create syntax
    syntax = DelimiterPreambleSyntax()

    # Setup registry with syntax and register block
    registry = Registry(syntax=syntax)
    registry.register("files_operations", FileOperations)

    # Create processor
    processor = StreamBlockProcessor(registry)

    # Test stream
    async def mock_stream() -> Any:
        lines = [
            "Some text before block.",
            "",
            "!!file01:files_operations",
            "src/main.py:C",
            "src/utils.py:E",
            "!!end",
            "",
            "More text after block.",
        ]

        for line in lines:
            yield line + "\n"

    # Process stream
    events = []
    async for event in processor.process_stream(mock_stream()):
        events.append(event)

    # Check events
    text_content_events = [e for e in events if e.type == EventType.TEXT_CONTENT]
    block_end_events = [e for e in events if e.type == EventType.BLOCK_END]

    # We get more events because of how line splitting works - that's OK
    assert len(block_end_events) == 1  # One block extracted
    assert any(e.content == "Some text before block." for e in text_content_events)
    assert any(e.content == "More text after block." for e in text_content_events)

    # Check extracted block
    extracted_event = block_end_events[0]
    assert isinstance(extracted_event, BlockEndEvent)
    block = extracted_event.get_block()

    assert block is not None
    assert block.syntax_name == "DelimiterPreambleSyntax"
    assert block.metadata.id == "file01"
    assert block.metadata.block_type == "files_operations"
    assert len(block.content.operations) == 2
    assert block.content.operations[0].path == "src/main.py"
    assert block.content.operations[0].action == "create"
    assert block.content.operations[1].path == "src/utils.py"
    assert block.content.operations[1].action == "edit"


@pytest.mark.asyncio
async def test_multiple_blocks() -> None:
    """Test processing multiple blocks in a stream."""
    syntax = DelimiterPreambleSyntax()

    registry = Registry(syntax=syntax)
    registry.register("files_operations", FileOperations)
    processor = StreamBlockProcessor(registry)

    async def mock_stream() -> Any:
        text = """!!block1:files_operations
file1.py:C
!!end

Some text between blocks.

!!block2:files_operations
file2.py:E
file3.py:D
!!end"""

        for line in text.split("\n"):
            yield line + "\n"

    extracted_blocks = []
    async for event in processor.process_stream(mock_stream()):
        if event.type == EventType.BLOCK_END:
            assert isinstance(event, BlockEndEvent)
            block = event.get_block()
            if block:
                extracted_blocks.append(block)

    assert len(extracted_blocks) == 2
    assert extracted_blocks[0].metadata.id == "block1"
    assert extracted_blocks[1].metadata.id == "block2"
    assert len(extracted_blocks[0].content.operations) == 1
    assert len(extracted_blocks[1].content.operations) == 2


@pytest.mark.asyncio
async def test_unclosed_block_rejection() -> None:
    """Test that unclosed blocks are rejected."""
    syntax = DelimiterPreambleSyntax()

    registry = Registry(syntax=syntax)
    registry.register("files_operations", FileOperations)
    processor = StreamBlockProcessor(registry)

    async def mock_stream() -> Any:
        text = """!!unclosed:files_operations
file1.py:C
file2.py:E"""

        for line in text.split("\n"):
            yield line + "\n"

    events = []
    async for event in processor.process_stream(mock_stream()):
        events.append(event)

    error_events = [e for e in events if e.type == EventType.BLOCK_ERROR]
    assert len(error_events) == 1
    assert "Stream ended without closing marker" in error_events[0].reason


if __name__ == "__main__":
    asyncio.run(test_basic_delimiter_preamble_syntax())
