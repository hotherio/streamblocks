# Block Collections

This directory contains block definitions organized by application domain. Blocks are **not part of the core StreamBlocks library** - they are examples of how to build domain-specific blocks using the core primitives.

## Philosophy

StreamBlocks provides the foundation for extracting structured blocks from text streams:
- Base classes: `Block`, `BaseMetadata`, `BaseContent`
- Processing: `Registry`, `StreamBlockProcessor`
- Syntaxes: `DelimiterFrontmatterSyntax`, `MarkdownFrontmatterSyntax`, etc.

The actual block definitions (what types of blocks you want to extract) are application-specific. This directory provides ready-to-use blocks for common domains.

## Available Collections

### agent/

Blocks for AI agent applications:
- **FileOperations** - Track file create/edit/delete operations
- **FileContent** - Store file content
- **Patch** - Code diffs and modifications
- **ToolCall** - External tool invocation with parameters
- **Memory** - Context storage/recall operations
- **Message** - AI-to-user communication (info, warning, error, success)
- **Visualization** - Charts, diagrams, tables, ASCII art
- **Interactive blocks** - YesNo, Choice, MultiChoice, Input, Scale, Ranking, Confirm, Form
- **StructuredOutput** - Dynamic schema-based blocks via `create_structured_output_block()`

## Usage

```python
from hother.streamblocks_examples.blocks.agent import FileOperations, Message, ToolCall

# Register blocks with your registry
registry.register("files_operations", FileOperations)
registry.register("message", Message)
registry.register("toolcall", ToolCall)
```

## Creating Custom Blocks

To create your own blocks for a different domain, follow this pattern:

```python
from typing import Literal
from hother.streamblocks import Block, BaseContent, BaseMetadata

class MyMetadata(BaseMetadata):
    """Metadata for my custom block."""
    block_type: Literal["my_block"] = "my_block"
    custom_field: str

class MyContent(BaseContent):
    """Content for my custom block."""
    parsed_data: dict = {}

    @classmethod
    def parse(cls, raw_text: str) -> "MyContent":
        # Parse raw_text into structured data
        return cls(raw_content=raw_text, parsed_data={})

class MyBlock(Block[MyMetadata, MyContent]):
    """My custom block type."""
```

## Copying to Your Project

For production use, we recommend copying the blocks you need into your own project rather than importing from `hother.streamblocks_examples`:

```bash
# Copy the agent blocks to your project
cp -r src/hother/streamblocks_examples/blocks/agent/ myproject/blocks/
```

Then update imports to your local path.
