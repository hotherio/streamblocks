"""Tests for minimal API and base classes."""

import asyncio
from typing import Any

import pytest
from pydantic import BaseModel, Field

from hother.streamblocks import (
    BlockEndEvent,
    DelimiterFrontmatterSyntax,
    DelimiterPreambleSyntax,
    EventType,
    MarkdownFrontmatterSyntax,
    Registry,
    StreamBlockProcessor,
)
from hother.streamblocks.core.models import Block
from hother.streamblocks.core.types import BaseContent, BaseMetadata


@pytest.mark.asyncio
async def test_minimal_api_no_models() -> None:
    """Test using syntax with no custom models."""
    # Create syntax with no parameters - uses BaseMetadata and BaseContent
    syntax = DelimiterPreambleSyntax()

    # Create type-specific registry (no blocks registered, will use base classes)
    registry = Registry(syntax=syntax)

    processor = StreamBlockProcessor(registry)

    async def mock_stream() -> Any:
        text = """!!note01:notes
This is a simple note.
No custom models needed.
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

    assert len(extracted_blocks) == 1
    block = extracted_blocks[0]

    # Check metadata has standard fields from BaseMetadata
    assert block.metadata.id == "note01"
    assert block.metadata.block_type == "notes"

    # Check data has raw_content from BaseContent
    # The content preserves original formatting including empty lines
    lines = block.content.raw_content.strip().split("\n")
    assert len(lines) == 3  # Two text lines and one empty line between
    assert lines[0] == "This is a simple note."
    assert lines[1] == ""
    assert lines[2] == "No custom models needed."


@pytest.mark.asyncio
async def test_missing_required_fields_delimiter_frontmatter() -> None:
    """Test that missing id and block_type cause validation failure for DelimiterFrontmatterSyntax."""
    from pydantic import ValidationError

    from hother.streamblocks import BlockErrorEvent

    # Use base classes (no custom models)
    syntax = DelimiterFrontmatterSyntax()

    # Create type-specific registry (no blocks registered, will use base classes)
    registry = Registry(syntax=syntax)

    processor = StreamBlockProcessor(registry)

    async def mock_stream() -> Any:
        # Note: No id or block_type in metadata - these are required!
        text = """!!start
---
priority: high
assignee: john
---
- Complete the report
- Review code changes
!!end"""

        for line in text.split("\n"):
            yield line + "\n"

    extracted_blocks = []
    error_events = []
    async for event in processor.process_stream(mock_stream()):
        if event.type == EventType.BLOCK_END:
            assert isinstance(event, BlockEndEvent)
            block = event.get_block()
            if block:
                extracted_blocks.append(block)
        elif event.type == EventType.BLOCK_ERROR:
            assert isinstance(event, BlockErrorEvent)
            error_events.append(event)

    # Block should be rejected due to missing required fields
    assert len(extracted_blocks) == 0
    assert len(error_events) == 1
    assert isinstance(error_events[0].exception, ValidationError)
    assert "id" in str(error_events[0].exception)
    assert "block_type" in str(error_events[0].exception)


@pytest.mark.asyncio
async def test_missing_required_fields_markdown() -> None:
    """Test that missing id and block_type cause validation failure for MarkdownFrontmatterSyntax."""
    from pydantic import ValidationError

    from hother.streamblocks import BlockErrorEvent

    # Use base classes with info string
    syntax = MarkdownFrontmatterSyntax(info_string="python")

    # Create type-specific registry (no blocks registered, will use base classes)
    registry = Registry(syntax=syntax)

    processor = StreamBlockProcessor(registry)

    async def mock_stream() -> Any:
        # Note: No id or block_type in metadata - these are required!
        text = """```python
---
author: alice
---
def hello():
    print("Hello, world!")
```"""

        for line in text.split("\n"):
            yield line + "\n"

    extracted_blocks = []
    error_events = []
    async for event in processor.process_stream(mock_stream()):
        if event.type == EventType.BLOCK_END:
            assert isinstance(event, BlockEndEvent)
            block = event.get_block()
            if block:
                extracted_blocks.append(block)
        elif event.type == EventType.BLOCK_ERROR:
            assert isinstance(event, BlockErrorEvent)
            error_events.append(event)

    # Block should be rejected due to missing required fields
    assert len(extracted_blocks) == 0
    assert len(error_events) == 1
    assert isinstance(error_events[0].exception, ValidationError)
    assert "id" in str(error_events[0].exception)
    assert "block_type" in str(error_events[0].exception)


@pytest.mark.asyncio
async def test_custom_metadata_inherits_base() -> None:
    """Test custom metadata class that inherits from BaseMetadata."""

    class CustomMetadata(BaseMetadata):
        priority: str = Field(default="normal")
        tags: list[str] = Field(default_factory=list)

        model_config = {"extra": "allow"}

    class CustomBlock(Block[CustomMetadata, BaseContent]):
        pass

    syntax = DelimiterPreambleSyntax()
    registry = Registry(syntax=syntax)
    registry.register("custom", CustomBlock)

    processor = StreamBlockProcessor(registry)

    async def mock_stream() -> Any:
        text = """!!task01:custom:urgent:backend
Task content here.
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

    assert len(extracted_blocks) == 1
    block = extracted_blocks[0]

    # Check inherited fields work
    assert block.metadata.id == "task01"
    assert block.metadata.block_type == "custom"

    # Check custom fields from metadata
    assert block.metadata.priority == "normal"  # Default value
    assert block.metadata.tags == []  # Default empty list

    # Check param fields from delimiter syntax
    assert hasattr(block.metadata, "param_0")
    assert block.metadata.param_0 == "urgent"
    assert hasattr(block.metadata, "param_1")
    assert block.metadata.param_1 == "backend"


def create_todo_block_setup() -> StreamBlockProcessor:
    """Create TodoBlock class and registry for testing."""

    class TodoItem(BaseModel):
        text: str
        done: bool = False

    class TodoContent(BaseContent):
        items: list[TodoItem] = Field(default_factory=list)

        @classmethod
        def parse(cls, raw_text: str) -> "TodoContent":
            items = []
            for line in raw_text.strip().split("\n"):
                line = line.strip()
                if line.startswith("- [ ] "):
                    items.append(TodoItem(text=line[6:], done=False))
                elif line.startswith("- [x] "):
                    items.append(TodoItem(text=line[6:], done=True))
                elif line.startswith("- "):
                    items.append(TodoItem(text=line[2:], done=False))
            return cls(raw_content=raw_text, items=items)

    class TodoBlock(Block[BaseMetadata, TodoContent]):
        pass

    syntax = DelimiterPreambleSyntax()
    registry = Registry(syntax=syntax)
    registry.register("todos", TodoBlock)

    return StreamBlockProcessor(registry)


@pytest.mark.asyncio
async def test_custom_content_inherits_base_extraction() -> None:
    """Test that custom TodoContent blocks can be extracted."""
    processor = create_todo_block_setup()

    async def mock_stream() -> Any:
        text = """!!todo01:todos
- [ ] Buy groceries
- [x] Call mom
- Finish report
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

    assert len(extracted_blocks) == 1
    assert hasattr(extracted_blocks[0].content, "items")


@pytest.mark.asyncio
async def test_custom_content_preserves_raw_content() -> None:
    """Test that custom content preserves raw_content field."""
    processor = create_todo_block_setup()

    async def mock_stream() -> Any:
        text = """!!todo01:todos
- [ ] Buy groceries
- [x] Call mom
- Finish report
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

    block = extracted_blocks[0]
    lines = block.content.raw_content.strip().split("\n")
    assert len(lines) == 5
    assert lines[0] == "- [ ] Buy groceries"
    assert lines[2] == "- [x] Call mom"
    assert lines[4] == "- Finish report"


@pytest.mark.asyncio
async def test_custom_content_parses_items() -> None:
    """Test that TodoContent correctly parses todo items."""
    processor = create_todo_block_setup()

    async def mock_stream() -> Any:
        text = """!!todo01:todos
- [ ] Buy groceries
- [x] Call mom
- Finish report
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

    block = extracted_blocks[0]
    assert len(block.content.items) == 3
    assert block.content.items[0].text == "Buy groceries"
    assert block.content.items[0].done is False
    assert block.content.items[1].text == "Call mom"
    assert block.content.items[1].done is True
    assert block.content.items[2].text == "Finish report"
    assert block.content.items[2].done is False


# NOTE: The test for multiple syntaxes handling the same block type
# has been removed as the new design supports only one syntax per processor.


if __name__ == "__main__":
    asyncio.run(test_minimal_api_no_models())
