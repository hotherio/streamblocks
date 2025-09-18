"""Tests for minimal API and base classes."""

import asyncio
from typing import Any

import pytest
from pydantic import BaseModel, Field

from streamblocks import (
    BlockRegistry,
    DelimiterFrontmatterSyntax,
    DelimiterPreambleSyntax,
    EventType,
    MarkdownFrontmatterSyntax,
    StreamBlockProcessor,
)
from streamblocks.core.models import BaseContent, BaseMetadata


@pytest.mark.asyncio
async def test_minimal_api_no_models() -> None:
    """Test using syntax with no custom models."""
    registry = BlockRegistry()
    
    # Register syntax with no parameters - uses BaseMetadata and BaseContent
    syntax = DelimiterPreambleSyntax()
    registry.register_syntax(syntax, block_types=["notes"], priority=1)
    
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
            extracted_blocks.append(event.metadata["extracted_block"])
    
    assert len(extracted_blocks) == 1
    block = extracted_blocks[0]
    
    # Check metadata is BaseMetadata with standard fields
    assert type(block.metadata).__name__ == "BaseMetadata"
    assert block.metadata.id == "note01"
    assert block.metadata.block_type == "notes"
    
    # Check content is BaseContent with raw_content
    assert type(block.content).__name__ == "BaseContent"
    # The content preserves original formatting including empty lines
    lines = block.content.raw_content.strip().split("\n")
    assert len(lines) == 3  # Two text lines and one empty line between
    assert lines[0] == "This is a simple note."
    assert lines[1] == ""
    assert lines[2] == "No custom models needed."


@pytest.mark.asyncio
async def test_auto_populated_fields_delimiter_frontmatter() -> None:
    """Test that id and block_type are auto-populated for DelimiterFrontmatterSyntax."""
    registry = BlockRegistry()
    
    # Use base classes (no custom models)
    syntax = DelimiterFrontmatterSyntax()
    registry.register_syntax(syntax, block_types=["tasks"], priority=1)
    
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
            extracted_blocks.append(event.metadata["extracted_block"])
    
    assert len(extracted_blocks) == 1
    block = extracted_blocks[0]
    
    # Check auto-populated fields
    assert block.metadata.id.startswith("block_")  # Auto-generated hash-based ID
    assert block.metadata.block_type == "unknown"  # Default when not specified


@pytest.mark.asyncio
async def test_auto_populated_fields_markdown() -> None:
    """Test that id and block_type are auto-populated for MarkdownFrontmatterSyntax."""
    registry = BlockRegistry()
    
    # Use base classes with info string
    syntax = MarkdownFrontmatterSyntax(info_string="python")
    registry.register_syntax(syntax, block_types=["python"], priority=1)
    
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
            extracted_blocks.append(event.metadata["extracted_block"])
    
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
    
    registry = BlockRegistry()
    syntax = DelimiterPreambleSyntax(metadata_class=CustomMetadata)
    registry.register_syntax(syntax, block_types=["custom"], priority=1)
    
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
            extracted_blocks.append(event.metadata["extracted_block"])
    
    assert len(extracted_blocks) == 1
    block = extracted_blocks[0]
    
    # Check it's our custom class
    assert type(block.metadata).__name__ == "CustomMetadata"
    
    # Check inherited fields work
    assert block.metadata.id == "task01"
    assert block.metadata.block_type == "custom"
    
    # Check custom fields
    assert block.metadata.priority == "normal"  # Default value
    assert block.metadata.tags == []  # Default empty list
    
    # Check param fields from delimiter syntax
    assert hasattr(block.metadata, "param_0")
    assert getattr(block.metadata, "param_0") == "urgent"
    assert hasattr(block.metadata, "param_1")
    assert getattr(block.metadata, "param_1") == "backend"


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
    
    registry = BlockRegistry()
    syntax = DelimiterPreambleSyntax(content_class=TodoContent)
    registry.register_syntax(syntax, block_types=["todos"], priority=1)
    
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
            extracted_blocks.append(event.metadata["extracted_block"])
    
    assert len(extracted_blocks) == 1
    block = extracted_blocks[0]
    
    # Check it's our custom class
    assert type(block.content).__name__ == "TodoContent"
    
    # Check raw_content is preserved (with extra newlines from stream processing)
    # The exact content depends on how lines are processed
    lines = block.content.raw_content.strip().split("\n")
    assert len(lines) == 5  # 3 todo items + 2 empty lines between them
    assert lines[0] == "- [ ] Buy groceries"
    assert lines[2] == "- [x] Call mom"  
    assert lines[4] == "- Finish report"
    
    # Check parsed items
    assert len(block.content.items) == 3
    assert block.content.items[0].text == "Buy groceries"
    assert block.content.items[0].done is False
    assert block.content.items[1].text == "Call mom"
    assert block.content.items[1].done is True
    assert block.content.items[2].text == "Finish report"
    assert block.content.items[2].done is False


@pytest.mark.asyncio
async def test_multiple_syntaxes_same_block_type() -> None:
    """Test that multiple syntaxes can handle the same block type."""
    registry = BlockRegistry()
    
    # Register two syntaxes for "notes" block type
    syntax1 = DelimiterPreambleSyntax()
    syntax2 = MarkdownFrontmatterSyntax()
    
    registry.register_syntax(syntax1, block_types=["notes"], priority=2)
    registry.register_syntax(syntax2, block_types=["notes"], priority=1)
    
    processor = StreamBlockProcessor(registry)
    
    async def mock_stream() -> Any:
        text = """!!note01:notes
Delimiter style note.
!!end

```
---
id: note02
block_type: notes
---
Markdown style note.
```"""
        
        for line in text.split("\n"):
            yield line + "\n"
    
    extracted_blocks = []
    async for event in processor.process_stream(mock_stream()):
        if event.type == EventType.BLOCK_EXTRACTED:
            extracted_blocks.append(event.metadata["extracted_block"])
    
    assert len(extracted_blocks) == 2
    
    # First block uses delimiter syntax
    assert extracted_blocks[0].syntax_name == "delimiter_preamble_!!"
    assert extracted_blocks[0].metadata.id == "note01"
    assert extracted_blocks[0].content.raw_content.strip() == "Delimiter style note."
    
    # Second block uses markdown syntax
    assert extracted_blocks[1].syntax_name == "markdown_frontmatter"
    # The YAML frontmatter should provide id and block_type
    assert extracted_blocks[1].metadata.id == "note02"
    assert extracted_blocks[1].metadata.block_type == "notes"
    assert extracted_blocks[1].content.raw_content.strip() == "Markdown style note."


if __name__ == "__main__":
    asyncio.run(test_minimal_api_no_models())