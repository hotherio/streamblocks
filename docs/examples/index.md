# Examples

Streamblocks comes with a comprehensive collection of examples organized by topic.

## Running Examples

```bash
# Run all examples (skip API-dependent ones)
uv run python examples/run_examples.py --skip-api

# Run specific category
uv run python examples/run_examples.py --category 00_basics

# Dry run to see what would be executed
uv run python examples/run_examples.py --dry-run
```

## Example Categories

### [00_basics](basic.md) - Getting Started

Foundational examples covering core concepts:

- Basic usage and core concepts
- Minimal API examples
- Error handling patterns
- Structured output

### [01_syntaxes](syntaxes.md) - Syntax Formats

Different block syntax formats:

- Markdown frontmatter
- Delimiter frontmatter
- Parsing decorators

### [02_adapters](adapters.md) - Stream Adapters

Working with different AI providers:

- Identity adapter (plain text)
- Gemini adapter
- OpenAI adapter
- Anthropic adapter
- Custom adapters

### [03_content](../patterns.md) - Content Processing

Content manipulation and processing:

- Patch content operations

### [04_logging](../advanced.md#logging-integration) - Logging

Different logging approaches:

- stdlib logging
- structlog integration
- Custom loggers

### [05_integrations](integrations.md) - Framework Integration

Integration with other libraries:

- PydanticAI integration

### [06_providers](../advanced.md#stream-adapters) - AI Providers

Complete examples with AI providers:

- Gemini demos
- Multi-call examples

### [07_ui](../advanced.md) - User Interface

Building interactive applications:

- Interactive blocks (CLI)
- Textual TUI demo

## Learning Path

For the best learning experience:

1. Start with **00_basics** to understand core concepts
2. Explore **01_syntaxes** for different block formats
3. Learn **02_adapters** for provider integration
4. See **05_integrations** for framework usage

## API Keys

Some examples require API keys. See [API Keys](../installation.md) for setup instructions.
