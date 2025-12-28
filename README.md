# Streamblocks

[![PyPI version](https://img.shields.io/pypi/v/streamblocks?color=brightgreen)](https://pypi.org/project/streamblocks/)
[![Python Versions](https://img.shields.io/badge/python-3.13%20%7C%203.14-blue)](https://pypi.org/project/streamblocks/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/hotherio/streamblocks/actions/workflows/test.yaml/badge.svg?branch=main)](https://github.com/hotherio/streamblocks/actions/workflows/test.yaml)
[![codecov](https://codecov.io/github/hotherio/streamblocks/branch/main/graph/badge.svg?token=FF6P9JIHPT)](https://codecov.io/github/hotherio/streamblocks)
[![Docs](https://img.shields.io/badge/docs-streamblocks.hother.io-blue)](https://streamblocks.hother.io)

Real-time extraction and processing of structured blocks from text streams.

<div align="center">
  <a href="https://streamblocks.hother.io/">Documentation</a>
</div>

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Built-in Syntaxes](#built-in-syntaxes)
- [Event Types](#event-types)
- [Documentation](#documentation)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

## Features

- **Pluggable Syntax System**: Define your own block syntaxes or use built-in ones
- **Async Stream Processing**: Process text streams line-by-line with full async support
- **AI Provider Adapters**: Automatic adapter detection for Gemini, OpenAI, Anthropic
- **Type-Safe Models**: Use Pydantic models for block metadata and content
- **Event-Driven Architecture**: React to block detection, updates, completion, and rejection
- **Production Ready**: Comprehensive error handling, logging, and validation

## Installation

### Core Installation

```bash
pip install streamblocks
```

### Optional Extras

Streamblocks provides optional extras for AI provider integrations:

| Extra | Dependencies | Purpose |
|-------|-------------|---------|
| `gemini` | google-genai | Google Gemini stream processing |
| `openai` | openai | OpenAI stream processing |
| `anthropic` | anthropic | Anthropic Claude stream processing |
| `all-providers` | All above | All AI provider integrations |

### Installing with Extras

```bash
# Single provider
pip install streamblocks[gemini]

# Multiple providers
pip install streamblocks[gemini,openai]

# All providers
pip install streamblocks[all-providers]
```

## Quick Start

```python
import asyncio
from streamblocks import BlockRegistry, DelimiterPreambleSyntax, StreamBlockProcessor, EventType
from streamblocks.content import FileOperationsContent, FileOperationsMetadata

async def main():
    registry = BlockRegistry()
    syntax = DelimiterPreambleSyntax(
        metadata_class=FileOperationsMetadata,
        content_class=FileOperationsContent,
    )
    registry.register_syntax(syntax, block_types=["files_operations"])
    processor = StreamBlockProcessor(registry)

    async def text_stream():
        yield "!!file01:files_operations\n"
        yield "src/main.py:C\n"
        yield "!!end\n"

    async for event in processor.process_stream(text_stream()):
        if event.type == EventType.BLOCK_EXTRACTED:
            print(f"Block: {event.metadata['extracted_block'].metadata.id}")

asyncio.run(main())
```

## Built-in Syntaxes

| Syntax | Format | Use Case |
|--------|--------|----------|
| **Delimiter with Preamble** | `!!<id>:<type>\n...\n!!end` | Simple structured blocks |
| **Markdown with Frontmatter** | ` ```lang\n---\nkey: value\n---\n...\n``` ` | Code blocks with metadata |
| **Delimiter with Frontmatter** | `!!start\n---\nkey: value\n---\n...\n!!end` | Hybrid structured blocks |

## Event Types

- `RAW_TEXT` - Non-block text passed through
- `BLOCK_DELTA` - Partial block update (new line added)
- `BLOCK_EXTRACTED` - Complete block successfully extracted
- `BLOCK_REJECTED` - Block failed validation or stream ended

## Documentation

To build and serve the documentation locally:

```bash
uv sync --group doc
source .venv/bin/activate
mkdocs serve
```

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
