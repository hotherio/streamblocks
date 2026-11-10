# Streamblocks

[![PyPI version](https://img.shields.io/pypi/v/streamblocks?color=brightgreen)](https://pypi.org/project/streamblocks/)
[![Python Versions](https://img.shields.io/badge/python-3.13%20%7C%203.14-blue)](https://pypi.org/project/streamblocks/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/hotherio/streamblocks/actions/workflows/test.yaml/badge.svg?branch=main)](https://github.com/hotherio/streamblocks/actions/workflows/test.yaml)
[![codecov](https://codecov.io/github/hotherio/streamblocks/branch/main/graph/badge.svg?token=FF6P9JIHPT)](https://codecov.io/github/hotherio/streamblocks)
[![Docs](https://img.shields.io/badge/docs-streamblocks.hother.io-blue)](https://streamblocks.hother.io)

Real-time extraction and processing of structured blocks from text streams.

LLMs often embed structured data in their responses: file operations, code blocks, tool calls. Streamblocks extracts these blocks in real-time as the stream arrives, emitting events like `BLOCK_START`, `BLOCK_CONTENT_DELTA`, and `BLOCK_END`. Process a Gemini stream, detect `!!save:file\npath/to/file.py\n!!end` blocks, and react immediately, no need to wait for the full response.

<div align="center">
  <a href="https://streamblocks.hother.io/">Documentation</a>
</div>

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [More Examples](#more-examples)
- [Built-in Syntaxes](#built-in-syntaxes)
- [Event Types](#event-types)
- [Optional Extras](#optional-extras)
- [Documentation](#documentation)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

## Features

- **Pluggable Syntax System**: Define your own block syntaxes or use built-in ones
- **Async Stream Processing**: Process text streams line-by-line with full async support
- **AI Provider Adapters**: Automatic adapter detection for Gemini, OpenAI, Anthropic
- **AG-UI Protocol Support**: Bidirectional adapters that consume AG-UI streams and emit AG-UI events
- **Type-Safe Models**: Use Pydantic models for block metadata and content
- **Built-in Artifact Blocks**: Files, search/replace patches and documents, ready to register
- **Mid-Stream Validation**: Reject a block while it is still being written and stop the stream
- **Grammar Export**: Generate a GBNF grammar from the registry to constrain local models to well-formed blocks
- **Event-Driven Architecture**: React to block detection, updates, completion, and rejection
- **Production Ready**: Comprehensive error handling, logging, and validation

## Installation

```bash
pip install streamblocks
```

## Quick Start

```python
import asyncio
from collections.abc import AsyncIterator

from hother.streamblocks import BlockEndEvent, Registry, StreamBlockProcessor


async def main() -> None:
    # The default syntax is `!!<id>:<type>` ... `!!end`
    processor = StreamBlockProcessor(Registry())

    async def text_stream() -> AsyncIterator[str]:
        yield "Here is the file you asked for:\n"
        yield "!!file01:note\n"
        yield "hello world\n"
        yield "!!end\n"

    async for event in processor.process_stream(text_stream()):
        if isinstance(event, BlockEndEvent):
            print(f"Block extracted: {event.block_type} -> {event.content['raw_content']!r}")


asyncio.run(main())
```

## More Examples

### Typed Blocks

Describe a block with Pydantic models and register it. Metadata and content are validated when the block closes.

```python
import asyncio
from collections.abc import AsyncIterator

from hother.streamblocks import (
    BaseContent,
    BaseMetadata,
    Block,
    BlockEndEvent,
    DelimiterFrontmatterSyntax,
    Registry,
    StreamBlockProcessor,
)


class TaskMetadata(BaseMetadata):
    title: str = "Untitled"
    priority: str = "normal"


class TaskContent(BaseContent):
    description: str = ""

    @classmethod
    def parse(cls, raw_text: str) -> "TaskContent":
        return cls(raw_content=raw_text, description=raw_text.strip())


TaskBlock = Block[TaskMetadata, TaskContent]


async def main() -> None:
    registry = Registry(syntax=DelimiterFrontmatterSyntax())
    registry.register("task", TaskBlock)
    processor = StreamBlockProcessor(registry)

    async def text_stream() -> AsyncIterator[str]:
        yield "!!start\n---\nid: task-1\nblock_type: task\ntitle: Fix bug\npriority: high\n---\n"
        yield "Fix the login issue\n!!end\n"

    async for event in processor.process_stream(text_stream()):
        if isinstance(event, BlockEndEvent):
            block = event.get_block()
            if block:
                print(block.metadata.title, "-", block.content.description)


asyncio.run(main())
```

### Streaming Artifacts

Built-in blocks for files, patches and documents that a model writes inside its answer.

```python
import asyncio
from collections.abc import AsyncIterator

from hother.streamblocks import BlockEndEvent, Registry, StreamBlockProcessor, XmlTagSyntax
from hother.streamblocks.blocks.artifacts import ARTIFACT_BLOCKS


async def main() -> None:
    registry = Registry(syntax=XmlTagSyntax(), blocks=ARTIFACT_BLOCKS)
    processor = StreamBlockProcessor(registry)
    print(registry.to_prompt()[:60])  # the same registry documents the format for the model

    async def text_stream() -> AsyncIterator[str]:
        yield 'Here you go:\n<artifact type="file" path="src/main.py">\n'
        yield 'print("hello")\n</artifact>\n'

    async for event in processor.process_stream(text_stream()):
        if isinstance(event, BlockEndEvent):
            block = event.get_block()
            if block:
                print(block.metadata.path, "->", block.content.raw_content)


asyncio.run(main())
```

### Processing AI Provider Streams

```python
from google import genai

from hother.streamblocks import BlockEndEvent, BlockStartEvent, Registry, StreamBlockProcessor

processor = StreamBlockProcessor(Registry())
client = genai.Client(api_key="...")
response = await client.aio.models.generate_content_stream(
    model="gemini-2.5-flash",
    contents="Create a Python script",
)

# Adapter auto-detected for Gemini streams
async for event in processor.process_stream(response):
    if isinstance(event, BlockStartEvent):
        print(f"Block started: {event.block_id}")
    elif isinstance(event, BlockEndEvent):
        print(f"Block complete: {event.block_id}")
```

### Event Handling Pattern

```python
from hother.streamblocks import EventType

async for event in processor.process_stream(stream):
    match event.type:
        case EventType.TEXT_DELTA:
            print(event.delta, end="")
        case EventType.BLOCK_START:
            print(f"\n[Block {event.block_id} detected]")
        case EventType.BLOCK_CONTENT_DELTA:
            print(event.delta, end="")
        case EventType.BLOCK_END:
            print(f"\n[Block {event.block_id} complete]")
        case EventType.BLOCK_ERROR:
            print(f"\n[Block rejected: {event.reason}]")
```

### Using Markdown Frontmatter Syntax

```python
from hother.streamblocks import MarkdownFrontmatterSyntax, Registry, StreamBlockProcessor

# Each registry holds exactly one syntax
registry = Registry(syntax=MarkdownFrontmatterSyntax(fence="```", info_string="python"))
processor = StreamBlockProcessor(registry)

# Detects blocks like:
# ```python
# ---
# id: example
# block_type: python
# ---
# print("hello")
# ```
```

## Built-in Syntaxes

| Syntax | Format | Use Case |
|--------|--------|----------|
| **Delimiter with Preamble** | `!!<id>:<type>\n...\n!!end` | Simple structured blocks |
| **Markdown with Frontmatter** | ` ```lang\n---\nkey: value\n---\n...\n``` ` | Code blocks with metadata |
| **Delimiter with Frontmatter** | `!!start\n---\nkey: value\n---\n...\n!!end` | Hybrid structured blocks |
| **XML Tag** | `<artifact type="file" path="...">\n...\n</artifact>` | Artifacts (files, patches, documents) inside prose |

## Event Types

### Lifecycle Events

- `STREAM_STARTED` - Stream processing began
- `STREAM_FINISHED` - Stream processing completed
- `STREAM_ERROR` - Stream processing failed

### Text Events

- `TEXT_CONTENT` - Complete text content outside blocks
- `TEXT_DELTA` - Incremental text chunk

### Block Events

- `BLOCK_START` - Block header detected
- `BLOCK_HEADER_DELTA` - Block header line received
- `BLOCK_METADATA_DELTA` - Metadata line received
- `BLOCK_CONTENT_DELTA` - Content line received
- `BLOCK_METADATA_END` - Metadata section complete
- `BLOCK_CONTENT_END` - Content section complete
- `BLOCK_END` - Block fully extracted
- `BLOCK_ERROR` - Block extraction failed

### Custom

- `CUSTOM` - User-defined event

## Optional Extras

Streamblocks provides optional extras for AI provider integrations:

| Extra | Dependencies | Purpose |
|-------|-------------|---------|
| `gemini` | google-genai | Google Gemini stream processing |
| `openai` | openai | OpenAI stream processing |
| `anthropic` | anthropic | Anthropic Claude stream processing |
| `agui` | ag-ui | AG-UI protocol adapters |
| `all-providers` | All above | All AI provider integrations |

```bash
# Single provider
pip install streamblocks[gemini]

# Multiple providers
pip install streamblocks[gemini,openai]

# All providers
pip install streamblocks[all-providers]
```

## Documentation

To build and serve the documentation locally:

```bash
uv sync --group doc
brew install d2  # diagrams are rendered with d2 at build time
uv run mkdocs serve
```

The documentation is served at <http://127.0.0.1:7227>.

## Development

### Dependency Groups

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

### Quick Reference

**Available extras:** `gemini`, `openai`, `anthropic`, `all-providers`

**Available groups:** `dev`, `doc`

### Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=hother.streamblocks --cov-report=html

# Run examples
uv run python examples/run_examples.py --skip-api
```

### Release Process

This project uses [python-semantic-release](https://python-semantic-release.readthedocs.io/) for fully automated versioning and releases. Every commit to the `main` branch is analyzed using conventional commits, and releases are created automatically when needed.

#### How It Works

1. **Commit with conventional format** to the `main` branch
2. **GitHub Actions automatically** analyzes commits, determines version bump, creates tag, updates changelog, publishes to PyPI, and creates GitHub release
3. **Documentation** is automatically deployed when a release is published

#### Version Bumping Rules

| Commit Type | Version Bump | Example |
|-------------|--------------|---------|
| `feat:` | Minor | 0.5.0 → 0.6.0 |
| `fix:`, `perf:`, `refactor:` | Patch | 0.5.0 → 0.5.1 |
| `feat!:`, `BREAKING CHANGE:` | Major | 0.5.0 → 1.0.0 |
| `docs:`, `chore:`, `ci:`, `style:`, `test:` | No release | - |

### Documentation Deployment

Documentation is automatically built and deployed when:
- A release is published (triggered by semantic-release)
- Changes are pushed to `docs/`, `mkdocs.yml`, or the workflow file on `main`

## Development Practices

### Branching & Pull Requests

Each git branch should have the format `<tag>/item_<id>` with eventually a descriptive suffix.

We use a **Squash & Merge** approach.

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

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
