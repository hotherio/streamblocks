# StreamBlocks

Real-time extraction and processing of structured blocks from text streams.

## Overview

StreamBlocks is a Python 3.13+ library for detecting and extracting structured blocks from streaming text. It provides:

- **Pluggable syntax system** - Define your own block syntaxes or use built-in ones
- **Async stream processing** - Process text streams line-by-line with full async support
- **Type-safe metadata** - Use Pydantic models for block metadata and content
- **Event-driven architecture** - React to block detection, updates, completion, and rejection
- **Built-in syntaxes** - Delimiter preamble, Markdown frontmatter, and hybrid syntaxes

## Installation

```bash
pip install streamblocks
```

## Quick Start

```python
import asyncio
from streamblocks import (
    BlockRegistry,
    DelimiterPreambleSyntax,
    StreamBlockProcessor,
    EventType,
)
from streamblocks.content import FileOperationsContent, FileOperationsMetadata

async def main():
    # Setup registry
    registry = BlockRegistry()
    
    # Register a syntax
    syntax = DelimiterPreambleSyntax(
        metadata_class=FileOperationsMetadata,
        content_class=FileOperationsContent,
    )
    registry.register_syntax(syntax, block_types=["files_operations"])
    
    # Create processor
    processor = StreamBlockProcessor(registry)
    
    # Process a stream
    async def text_stream():
        text = """
!!file01:files_operations
src/main.py:C
src/utils.py:E
!!end
"""
        for line in text.strip().split("\n"):
            yield line + "\n"
    
    # Handle events
    async for event in processor.process_stream(text_stream()):
        if event.type == EventType.BLOCK_EXTRACTED:
            block = event.metadata["extracted_block"]
            print(f"Extracted block: {block.metadata.id}")
            for op in block.content.operations:
                print(f"  - {op.action}: {op.path}")

asyncio.run(main())
```

## Built-in Syntaxes

### 1. Delimiter with Preamble

```
!!<id>:<type>[:param1:param2...]
content
!!end
```

### 2. Markdown with Frontmatter

```markdown
```[info_string]
---
key: value
---
content
```
```

### 3. Delimiter with Frontmatter

```
!!start
---
key: value
---
content
!!end
```

## Creating Custom Content Models

```python
from pydantic import BaseModel
from typing import Literal

class MyMetadata(BaseModel):
    id: str
    block_type: Literal["my_type"]
    custom_field: str | None = None

class MyContent(BaseModel):
    data: str
    
    @classmethod
    def parse(cls, raw_text: str) -> "MyContent":
        # Custom parsing logic
        return cls(data=raw_text.strip())
```

## Event Types

- `RAW_TEXT` - Non-block text passed through
- `BLOCK_DELTA` - Partial block update (new line added)
- `BLOCK_EXTRACTED` - Complete block successfully extracted
- `BLOCK_REJECTED` - Block failed validation or stream ended

## Custom Validators

```python
def my_validator(metadata: BaseModel, content: BaseModel) -> bool:
    # Custom validation logic
    return True

registry.add_validator("my_type", my_validator)
```

## License

MIT