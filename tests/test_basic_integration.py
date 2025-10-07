"""Basic integration tests for StreamBlocks."""

import asyncio
from typing import Any

import pytest

from hother.streamblocks import (
    DelimiterPreambleSyntax,
    EventType,
    Registry,
    StreamBlockProcessor,
)
from hother.streamblocks.blocks import FileOperationsContent, FileOperationsMetadata


@pytest.mark.asyncio
async def test_basic_delimiter_preamble_syntax() -> None:
    """Test basic functionality with delimiter preamble syntax."""
    # Create syntax
    syntax = DelimiterPreambleSyntax(
        name="test_files_syntax",
        metadata_class=FileOperationsMetadata,
        content_class=FileOperationsContent,
    )

    # Setup registry with syntax
    registry = Registry(syntax)

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
    raw_text_events = [e for e in events if e.type == EventType.RAW_TEXT]
    [e for e in events if e.type == EventType.BLOCK_DELTA]
    block_extracted_events = [e for e in events if e.type == EventType.BLOCK_EXTRACTED]

    # We get more events because of how line splitting works - that's OK
    assert len(block_extracted_events) == 1  # One block extracted
    assert any(e.data == "Some text before block." for e in raw_text_events)
    assert any(e.data == "More text after block." for e in raw_text_events)

    # Check extracted block
    extracted_event = block_extracted_events[0]
    block = extracted_event.block

    assert block.syntax_name == "test_files_syntax"
    assert block.metadata.id == "file01"
    assert block.metadata.block_type == "files_operations"
    assert len(block.data.operations) == 2
    assert block.data.operations[0].path == "src/main.py"
    assert block.data.operations[0].action == "create"
    assert block.data.operations[1].path == "src/utils.py"
    assert block.data.operations[1].action == "edit"


@pytest.mark.asyncio
async def test_multiple_blocks() -> None:
    """Test processing multiple blocks in a stream."""
    syntax = DelimiterPreambleSyntax(
        name="test_files_syntax",
        metadata_class=FileOperationsMetadata,
        content_class=FileOperationsContent,
    )

    registry = Registry(syntax)
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
        if event.type == EventType.BLOCK_EXTRACTED:
            extracted_blocks.append(event.block)

    assert len(extracted_blocks) == 2
    assert extracted_blocks[0].metadata.id == "block1"
    assert extracted_blocks[1].metadata.id == "block2"
    assert len(extracted_blocks[0].data.operations) == 1
    assert len(extracted_blocks[1].data.operations) == 2


@pytest.mark.asyncio
async def test_unclosed_block_rejection() -> None:
    """Test that unclosed blocks are rejected."""
    syntax = DelimiterPreambleSyntax(
        name="test_files_syntax",
        metadata_class=FileOperationsMetadata,
        content_class=FileOperationsContent,
    )

    registry = Registry(syntax)
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

    rejected_events = [e for e in events if e.type == EventType.BLOCK_REJECTED]
    assert len(rejected_events) == 1
    assert "Stream ended without closing marker" in rejected_events[0].content["reason"]


if __name__ == "__main__":
    asyncio.run(test_basic_delimiter_preamble_syntax())
