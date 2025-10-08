"""Tests for minimal API and base classes."""

import asyncio
from typing import Any

import pytest
from pydantic import BaseModel, Field

from hother.streamblocks import (
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
        if event.type == EventType.BLOCK_EXTRACTED:
            extracted_blocks.append(event.block)

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
async def test_auto_populated_fields_delimiter_frontmatter() -> None:
    """Test that id and block_type are auto-populated for DelimiterFrontmatterSyntax."""
    # Use base classes (no custom models)
    syntax = DelimiterFrontmatterSyntax()

    # Create type-specific registry (no blocks registered, will use base classes)
    registry = Registry(syntax=syntax)

    processor = StreamBlockProcessor(registry)

    async def mock_stream() -> Any:
        # Note: No id or block_type in metadata!
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
    async for event in processor.process_stream(mock_stream()):
        if event.type == EventType.BLOCK_EXTRACTED:
            extracted_blocks.append(event.block)

    assert len(extracted_blocks) == 1
    block = extracted_blocks[0]

    # Check auto-populated fields
    assert block.metadata.id.startswith("block_")  # Auto-generated hash-based ID
    assert block.metadata.block_type == "unknown"  # Default when not specified


@pytest.mark.asyncio
async def test_auto_populated_fields_markdown() -> None:
    """Test that id and block_type are auto-populated for MarkdownFrontmatterSyntax."""
    # Use base classes with info string
    syntax = MarkdownFrontmatterSyntax(info_string="python")

    # Create type-specific registry (no blocks registered, will use base classes)
    registry = Registry(syntax=syntax)

    processor = StreamBlockProcessor(registry)

    async def mock_stream() -> Any:
        # Note: No id or block_type in metadata!
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
    async for event in processor.process_stream(mock_stream()):
        if event.type == EventType.BLOCK_EXTRACTED:
            extracted_blocks.append(event.block)

    assert len(extracted_blocks) == 1
    block = extracted_blocks[0]

    # Check auto-populated fields
    assert block.metadata.id.startswith("block_")  # Auto-generated hash-based ID
    assert block.metadata.block_type == "python"  # Inferred from info_string


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
        if event.type == EventType.BLOCK_EXTRACTED:
            extracted_blocks.append(event.block)

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


@pytest.mark.asyncio
async def test_custom_content_inherits_base() -> None:
    """Test custom content class that inherits from BaseContent."""

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

    processor = StreamBlockProcessor(registry)

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
        if event.type == EventType.BLOCK_EXTRACTED:
            extracted_blocks.append(event.block)

    assert len(extracted_blocks) == 1
    block = extracted_blocks[0]

    # Check content has items from TodoContent
    assert hasattr(block.content, "items")  # Custom field from TodoContent

    # Check raw_content is preserved (with extra newlines from stream processing)
    # The exact content depends on how lines are processed
    lines = block.content.raw_content.strip().split("\n")
    assert len(lines) == 5  # 3 todo items + 2 empty lines between them
    assert lines[0] == "- [ ] Buy groceries"
    assert lines[2] == "- [x] Call mom"
    assert lines[4] == "- Finish report"

    # Check parsed items from TodoContent
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
