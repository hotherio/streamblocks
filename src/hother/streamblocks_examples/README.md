# Streamblocks Examples

This directory contains example scripts demonstrating various features of Streamblocks, organized in a progressive learning path.

## Directory Structure

```
src/hother/streamblocks_examples/
├── 00_quickstart/          # Ultra-minimal examples (start here!)
│   ├── 01_hello_world.py
│   ├── 02_basic_stream.py
│   └── 03_custom_block.py
├── 01_basics/              # Core concepts and getting started
├── 02_syntaxes/            # Block syntax formats
├── 03_adapters/            # Stream adapters for AI providers
├── 04_blocks/              # Block type examples
├── 05_logging/             # Logging integration
├── 06_integrations/        # Framework integrations
├── 07_providers/           # AI provider demos
├── 08_ui/                  # User interface examples
├── 09_advanced/            # Advanced features
├── blocks/                 # Reusable block definitions
├── helpers/                # Stream generators and handlers
├── tools/                  # Tool implementations
└── run_examples.py         # Example runner script
```

## Key Concepts

Before diving into examples, understand these core Streamblocks concepts:

| Concept | Description |
|---------|-------------|
| **Block** | A structured region in a text stream (e.g., code fence, frontmatter) |
| **Syntax** | Rules for detecting and parsing blocks (delimiter, markdown, etc.) |
| **Registry** | Maps block types to block classes and validators |
| **Event** | Notifications during processing (start, delta, end, error) |
| **Adapter** | Extracts text from provider-specific streams (Gemini, OpenAI, etc.) |
| **Processor** | Main orchestrator that processes streams and emits events |

## Running Examples

### Quick Start

Run all standalone examples (no API keys required):

```bash
uv run python -m hother.streamblocks_examples.run_examples --skip-api
```

Run all examples (including API-dependent ones):

```bash
export GEMINI_API_KEY="your-key-here"  # pragma: allowlist secret
uv run python -m hother.streamblocks_examples.run_examples
```

### Runner Options

```bash
# Run all runnable examples
uv run python -m hother.streamblocks_examples.run_examples

# Run only adapter examples
uv run python -m hother.streamblocks_examples.run_examples --category 03_adapters

# Skip API-dependent examples
uv run python -m hother.streamblocks_examples.run_examples --skip-api

# Include TUI examples (will fail without interaction)
uv run python -m hother.streamblocks_examples.run_examples --include-ui

# Dry run (see what would be executed)
uv run python -m hother.streamblocks_examples.run_examples --dry-run

# Run examples in parallel (faster)
uv run python -m hother.streamblocks_examples.run_examples --parallel

# Custom timeout
uv run python -m hother.streamblocks_examples.run_examples --timeout 60

# Verbose output
uv run python -m hother.streamblocks_examples.run_examples --verbose

# JSON output (machine-readable)
uv run python -m hother.streamblocks_examples.run_examples --output json
```

### Using Pytest

Examples can also be run as pytest tests:

```bash
# Run all examples
pytest tests/test_examples.py

# Skip API-dependent examples
pytest tests/test_examples.py -m "not api"

# Skip TUI examples
pytest tests/test_examples.py -m "not ui"

# Skip slow examples
pytest tests/test_examples.py -m "not slow"

# Run in parallel with pytest-xdist
pytest tests/test_examples.py -n auto

# Verbose output
pytest tests/test_examples.py -v
```

## Example Categories

### 00_quickstart - Start Here!

Ultra-minimal examples (~40-50 lines each) to get started quickly:

- `01_hello_world.py` - Simplest working example
- `02_basic_stream.py` - Basic streaming
- `03_custom_block.py` - Define a custom block type

### 01_basics - Getting Started

Foundational examples to understand core Streamblocks concepts:

- `01_basic_usage.py` - Basic Streamblocks usage and core concepts
- `02_minimal_api.py` - Minimal API example for quick reference
- `03_error_handling.py` - Error handling patterns and best practices
- `04_structured_output.py` - Working with structured output

### 02_syntaxes - Syntax Formats

Examples showing different block syntax formats:

- `01_markdown_frontmatter.py` - Markdown frontmatter syntax
- `02_delimiter_frontmatter.py` - Delimiter with frontmatter syntax
- `03_parsing_decorators.py` - Using parsing decorators for custom parsers

### 03_adapters - Stream Adapters

Examples demonstrating stream adapters for different AI providers:

- `01_identity_adapter_plain_text.py` - Plain text streams (no adapter)
- `02_gemini_auto_detect.py` - **Requires GEMINI_API_KEY** - Gemini with auto-detection
- `03_openai_explicit_adapter.py` - **Requires OPENAI_API_KEY** - OpenAI with explicit adapter
- `04_anthropic_adapter.py` - **Requires ANTHROPIC_API_KEY** - Anthropic event streams
- And more...

### 05_logging - Logging Integration

- `01_stdlib_logging.py` - Python stdlib logging integration
- `02_structlog.py` - Structured logging with structlog
- `03_custom_logger.py` - Custom logger implementation

### 06_integrations - Framework Integrations

- `01_pydantic_ai_integration.py` - **Requires API keys** - PydanticAI integration

### 07_providers - AI Provider Demos

- `01_gemini_simple_demo.py` - **Requires GEMINI_API_KEY** - Simple Gemini demo
- `02_gemini_architect.py` - **Requires GEMINI_API_KEY** - Complex Gemini example

### 08_ui - User Interface

- `01_interactive_blocks.py` - Interactive block types (CLI output)
- `02_interactive_ui_demo.py` - **TUI - Cannot run automatically** - Full Textual UI demo

## Learning Path

For the best learning experience, we recommend following this order:

1. **Start with quickstart** (`00_quickstart/`)
2. **Learn basics** (`01_basics/`)
3. **Explore syntaxes** (`02_syntaxes/`)
4. **Master adapters** (`03_adapters/`)
5. **Explore integrations** (`06_integrations/`, `07_providers/`)
6. **Build UIs** (`08_ui/`)

## API Keys

Some examples require API keys from AI providers:

### Gemini (Google AI)

```bash
export GEMINI_API_KEY="your-key-here"  # pragma: allowlist secret
```

Get your key at: https://aistudio.google.com/apikey

### OpenAI

```bash
export OPENAI_API_KEY="your-key-here"  # pragma: allowlist secret
```

Get your key at: https://platform.openai.com/api-keys

### Anthropic

```bash
export ANTHROPIC_API_KEY="your-key-here"  # pragma: allowlist secret
```

Get your key at: https://console.anthropic.com/settings/keys

## Running Individual Examples

```bash
# Using module syntax (recommended)
uv run python -m hother.streamblocks_examples.00_quickstart.01_hello_world

# Direct path
uv run python src/hother/streamblocks_examples/01_basics/01_basic_usage.py
```

## CI/CD

For continuous integration, use the pytest integration:

```bash
pytest tests/test_examples.py -m "not api" -m "not ui"
```

## Contributing Examples

When adding new examples:

1. **Place in appropriate category folder** - Use numbered prefixes
2. **Use numbered file names** - Follow the pattern `NN_feature_name.py`
3. **Add docstring** - Explain what the example demonstrates
4. **Document requirements** - Note any API keys or special dependencies
5. **Make it runnable** - Include `if __name__ == "__main__":` block
6. **Test it** - Run with the example runner to verify
