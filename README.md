# Streamblocks

[![PyPI version](https://img.shields.io/pypi/v/streamblocks?color=brightgreen)](https://pypi.org/project/streamblocks/)
[![Python Versions](https://img.shields.io/badge/python-3.13%20%7C%203.14-blue)](https://pypi.org/project/streamblocks/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/streamblocks/streamblocks/actions/workflows/test.yaml/badge.svg?branch=main)](https://github.com/streamblocks/streamblocks/actions/workflows/test.yaml)
[![Coverage](https://codecov.io/gh/streamblocks/streamblocks/branch/main/graph/badge.svg)](https://codecov.io/gh/streamblocks/streamblocks)
[![Docs](https://img.shields.io/badge/docs-streamblocks.hother.io-blue)](https://streamblocks.hother.io)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Conventional Commits](https://img.shields.io/badge/Conventional%20Commits-1.0.0-blue.svg)](https://conventionalcommits.org)
[![Renovate enabled](https://img.shields.io/badge/renovate-enabled-brightgreen.svg)](https://renovatebot.com/)

Real-time extraction and processing of structured blocks from text streams.

## Overview

Streamblocks is a Python 3.13+ library for detecting and extracting structured blocks from streaming text. It provides:

- **Pluggable syntax system** - Define your own block syntaxes or use built-in ones
- **Async stream processing** - Process text streams line-by-line with full async support
- **Type-safe metadata** - Use Pydantic models for block metadata and content
- **Event-driven architecture** - React to block detection, updates, completion, and rejection
- **Built-in syntaxes** - Delimiter preamble, Markdown frontmatter, and hybrid syntaxes

## Installation

### Basic Installation

```bash
pip install streamblocks
```

### With AI Provider Support

Streamblocks supports multiple AI providers through optional dependencies:

```bash
# For Google Gemini (gemini-2.5-flash)
pip install streamblocks[gemini]

# For OpenAI (gpt-5-nano-2025-08-07)
pip install streamblocks[openai]

# For Anthropic Claude (claude-3.5-haiku)
pip install streamblocks[anthropic]

# All providers at once
pip install streamblocks[all-providers]

# Multiple specific providers
pip install streamblocks[gemini,openai]
```

### From Source

```bash
git clone https://github.com/streamblocks/streamblocks.git
cd streamblocks
pip install -e ".[all-providers]"
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

## Processing Modes

Streamblocks supports two processing modes to fit different use cases:

### 1. Automatic Stream Processing (Recommended)

Process entire streams automatically with `process_stream()`. This is the simplest and most common approach:

```python
from google import genai

# Get a stream from any AI provider
client = genai.Client(api_key=api_key)
response = await client.aio.models.generate_content_stream(
    model="gemini-2.5-flash",
    contents="Create a Python hello world script",
)

# Pass the stream directly - no wrapper function needed!
async for event in processor.process_stream(response):
    if event.type == EventType.BLOCK_EXTRACTED:
        print(f"Block: {event.block.metadata.id}")
```

**Benefits:**
- Automatic adapter detection for Gemini, OpenAI, Anthropic
- Original chunks preserved in event stream
- Handles all line accumulation and buffering
- Simplest API for most use cases

### 2. Manual Chunk Processing

For fine-grained control, process chunks one at a time with `process_chunk()`:

```python
processor = StreamBlockProcessor(registry)

async for chunk in response:
    # Process this chunk and get all resulting events
    events = processor.process_chunk(chunk)

    for event in events:
        if isinstance(event, BlockExtractedEvent):
            print(f"Block: {event.block.metadata.id}")

# Don't forget to finalize!
final_events = processor.finalize()
```

**When to use manual processing:**
- Custom buffering or batching strategies
- Selective processing based on chunk content
- Integration with existing async pipelines
- Processing chunks from multiple sources
- Need synchronous processing API

**Important:** Always call `finalize()` after processing all chunks to get rejection events for incomplete blocks.

See `examples/adapters/13_manual_chunk_processing.py` for detailed examples of manual processing patterns.

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

## Interactive Blocks

Streamblocks includes built-in support for interactive content blocks that can capture user interactions. These are useful for building conversational interfaces, forms, surveys, and other interactive applications.

### Available Interactive Block Types

1. **YesNo** - Simple yes/no questions
2. **Choice** - Single choice from multiple options
3. **MultiChoice** - Multiple selections from a list
4. **Input** - Text/number/email input fields
5. **Scale** - Numeric rating scales
6. **Ranking** - Rank items in order
7. **Confirm** - Confirmation dialogs
8. **Form** - Multi-field forms

### Interactive Block Example

```python
from streamblocks.content import YesNoMetadata, YesNoContent

# Example block in your text stream:
"""
!!start
---
id: setup-question
block_type: yesno
yes_label: "Continue"
no_label: "Skip"
---
prompt: "Would you like to configure settings now?"
!!end
"""
```

### Using Interactive Blocks

```python
import asyncio
from streamblocks import BlockRegistry, DelimiterFrontmatterSyntax, StreamBlockProcessor
from streamblocks.content import (
    YesNoMetadata, YesNoContent,
    ChoiceMetadata, ChoiceContent,
    # ... other interactive content types
)

# Set up registry with interactive block mapping
block_type_mapping = {
    "yesno": (YesNoMetadata, YesNoContent),
    "choice": (ChoiceMetadata, ChoiceContent),
    # ... other mappings
}

# Custom syntax that handles block type detection
class InteractiveSyntax(DelimiterFrontmatterSyntax):
    def parse_block(self, candidate):
        # Parse metadata to determine block type
        # Then use appropriate metadata/content classes
        # See examples/interactive_blocks_example.py for full implementation
        pass
```

### Interactive UI Example

The library includes a complete example of building an interactive terminal UI using Textual:

```bash
python examples/interactive_ui_demo.py
```

This demonstrates:
- Dynamic widget creation based on block types
- Response capture and validation
- History tracking
- Real-time stream processing

See `examples/interactive_blocks_example.py` for a simpler example of parsing interactive blocks.

## Development

### Dependency Groups

Streamblocks uses dependency groups for development and documentation:

| Group | Purpose | Key Dependencies |
|-------|---------|------------------|
| `dev` | Development tools | pytest, ruff, basedpyright, detect-secrets |
| `doc` | Documentation building | mkdocs, mkdocs-material, mike |

### Installation

**Basic development setup:**
```bash
uv sync --group dev
source .venv/bin/activate
lefthook install
```

**Full development setup with extras:**
```bash
uv sync --group dev --all-extras
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=hother.streamblocks --cov-report=html

# Run specific test file
uv run pytest tests/test_processor.py
```

### Code Quality

```bash
# Run pre-commit hooks
uv run lefthook run pre-commit --all-files -- --no-stash

# Run type checking
uv run basedpyright src

# Run examples
uv run python examples/run_examples.py --skip-api
```

### Conventional Commits

We use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring
- `test`: Test changes
- `chore`: Maintenance tasks

## Contributing

Contributions are welcome! Please ensure:
1. All tests pass (`uv run pytest`)
2. Code quality checks pass (`uv run lefthook run pre-commit --all-files -- --no-stash`)
3. Commits follow conventional commit format

## License

MIT
