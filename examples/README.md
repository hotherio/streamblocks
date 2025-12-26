# Streamblocks Examples

This directory contains example scripts demonstrating various features of Streamblocks, organized in a progressive learning path.

## Directory Structure

The examples are organized as a separate workspace package (`streamblocks-examples`):

```
examples/
├── pyproject.toml               # Examples package configuration
├── streamblocks_examples/       # Examples package directory
│   ├── 00_quickstart/          # Ultra-minimal examples (start here!)
│   │   ├── 01_hello_world.py
│   │   ├── 02_basic_stream.py
│   │   └── 03_custom_block.py
│   ├── 01_basics/              # Core concepts and getting started
│   │   ├── 01_basic_usage.py
│   │   ├── 02_minimal_api.py
│   │   ├── 03_error_handling.py
│   │   └── 04_structured_output.py
│   ├── 02_syntaxes/            # Block syntax formats
│   │   ├── 01_markdown_frontmatter.py
│   │   ├── 02_delimiter_frontmatter.py
│   │   └── 03_parsing_decorators.py
│   ├── 03_adapters/            # Stream adapters for AI providers
│   │   ├── 01_identity_adapter_plain_text.py
│   │   ├── 02_gemini_auto_detect.py      # Requires API key
│   │   └── ...
│   ├── 04_blocks/              # Block type examples
│   ├── 05_logging/             # Logging integration
│   ├── 06_integrations/        # Framework integrations
│   ├── 07_providers/           # AI provider demos
│   ├── 08_ui/                  # User interface examples
│   ├── 09_advanced/            # Advanced features
│   ├── helpers/                # Reusable stream generators and handlers
│   └── tools/                  # Tool implementations
└── run_examples.py             # Example runner script
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
# From project root
uv run python examples/run_examples.py --skip-api
```

Run all examples (including API-dependent ones):

```bash
export GEMINI_API_KEY="your-key-here"
uv run python examples/run_examples.py
```

### Runner Options

The `run_examples.py` script provides flexible control over example execution:

```bash
# Run all runnable examples
uv run python examples/run_examples.py

# Run only adapter examples
uv run python examples/run_examples.py --category 03_adapters

# Skip API-dependent examples
uv run python examples/run_examples.py --skip-api

# Include TUI examples (will fail without interaction)
uv run python examples/run_examples.py --include-ui

# Dry run (see what would be executed)
uv run python examples/run_examples.py --dry-run

# Run examples in parallel (faster)
uv run python examples/run_examples.py --parallel

# Custom timeout
uv run python examples/run_examples.py --timeout 60

# Verbose output
uv run python examples/run_examples.py --verbose

# JSON output (machine-readable)
uv run python examples/run_examples.py --output json

# Text output (default, human-readable with colors)
uv run python examples/run_examples.py --output text
```

### Output Formats

The runner supports two output formats:

- **text** (default): Human-readable colored output with progress indicators
- **json**: Machine-readable structured output with timing data

JSON output format:
```json
{
  "summary": {
    "total": 23,
    "passed": 23,
    "failed": 0,
    "skipped": 8
  },
  "results": [
    {
      "path": "examples/03_adapters/01_identity_adapter_plain_text.py",
      "status": "pass",
      "category": "03_adapters",
      "duration": 0.82
    }
  ],
  "skipped": [
    {
      "path": "streamblocks_examples/08_ui/02_interactive_ui_demo.py",
      "reason": "TUI example (requires user interaction)",
      "category": "08_ui"
    }
  ]
}
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
- `05_mixed_event_stream.py` - Working with mixed event streams
- `06_text_delta_streaming.py` - Real-time text delta events
- `07_block_opened_event.py` - Detecting block opening
- `08_configuration_flags.py` - Processor configuration options
- `09_custom_adapter.py` - Creating custom adapters
- `10_callable_adapter.py` - Using callable adapters
- `11_attribute_adapter_generic.py` - Generic attribute adapters
- `12_disable_original_events.py` - Controlling event emission
- `13_manual_chunk_processing.py` - **Requires GEMINI_API_KEY** - Manual chunk processing

### 04_content - Content Processing

Examples for content manipulation and processing:

- `01_patch_content.py` - Patch content operations

### 05_logging - Logging Integration

Examples demonstrating different logging approaches:

- `01_stdlib_logging.py` - Python stdlib logging integration
- `02_structlog.py` - Structured logging with structlog
- `03_custom_logger.py` - Custom logger implementation

### 06_integrations - Framework Integrations

Examples showing integration with other libraries:

- `01_pydantic_ai_integration.py` - **Requires API keys** - PydanticAI integration

### 07_providers - AI Provider Demos

Complete examples with AI providers:

- `01_gemini_simple_demo.py` - **Requires GEMINI_API_KEY** - Simple Gemini demo
- `02_gemini_architect.py` - **Requires GEMINI_API_KEY** - Complex Gemini example with multiple calls

### 08_ui - User Interface

User interface examples:

- `01_interactive_blocks.py` - Interactive block types (CLI output)
- `02_interactive_ui_demo.py` - **TUI - Cannot run automatically** - Full Textual UI demo

## Learning Path

For the best learning experience, we recommend following this order:

1. **Start with quickstart** (`00_quickstart/`)
   - Run `01_hello_world.py` for the simplest example
   - See basic streaming in `02_basic_stream.py`

2. **Learn basics** (`01_basics/`)
   - Understand core concepts with `01_basic_usage.py`
   - See the minimal API with `02_minimal_api.py`

3. **Explore syntaxes** (`02_syntaxes/`)
   - Explore different block formats
   - Understand parsing decorators

4. **Master adapters** (`03_adapters/`)
   - Start with plain text (`01_identity_adapter_plain_text.py`)
   - Progress to provider-specific adapters
   - Learn custom adapter creation

5. **Explore integrations** (`06_integrations/`, `07_providers/`)
   - See real-world usage with AI providers
   - Integrate with frameworks like PydanticAI

6. **Build UIs** (`08_ui/`)
   - Create interactive applications

## API Keys

Some examples require API keys from AI providers:

### Gemini (Google AI)

```bash
export GEMINI_API_KEY="your-key-here"
# or
export GOOGLE_API_KEY="your-key-here"
```

Get your key at: https://aistudio.google.com/apikey

### OpenAI

```bash
export OPENAI_API_KEY="your-key-here"
```

Get your key at: https://platform.openai.com/api-keys

### Anthropic

```bash
export ANTHROPIC_API_KEY="your-key-here"
```

Get your key at: https://console.anthropic.com/settings/keys

## Running Individual Examples

You can always run examples directly:

```bash
# Simple example (no API key)
uv run python examples/streamblocks_examples/01_basics/01_basic_usage.py

# API example (requires key)
export GEMINI_API_KEY="your-key-here"
uv run python examples/streamblocks_examples/07_providers/01_gemini_simple_demo.py

# Or using the module syntax
uv run python -m streamblocks_examples.01_basics.01_basic_usage
```

## Configuration

The `.examples.yaml` file in the project root allows fine-grained control:

- Custom timeouts for specific examples
- Skip lists
- API key requirements
- Category definitions

## CI/CD

For continuous integration, use the pytest integration:

```bash
# In CI pipeline
pytest tests/test_examples.py -m "not api" -m "not ui"
```

This will:
- Skip examples requiring API keys
- Skip TUI examples
- Provide structured test results
- Generate JUnit XML reports with `--junitxml=report.xml`

## Troubleshooting

### Example times out

Increase the timeout:

```bash
uv run python examples/run_examples.py --timeout 120
```

### API rate limits

If you hit API rate limits, run examples sequentially without `--parallel`:

```bash
uv run python examples/run_examples.py
```

### Import errors

Make sure you've installed all dependencies:

```bash
uv pip install -e ".[dev,gemini,openai,anthropic]"
```

## Contributing Examples

When adding new examples:

1. **Place in appropriate category folder** - Use numbered prefixes (e.g., `01_basics/`, `03_adapters/`)
2. **Use numbered file names** - Follow the pattern `NN_feature_name.py` (e.g., `14_new_feature.py`)
3. **Add docstring** - Explain what the example demonstrates
4. **Document requirements** - Note any API keys or special dependencies
5. **Make it runnable** - Include `if __name__ == "__main__":` block
6. **Test it** - Run with `uv run python examples/run_examples.py` to verify

The runner will automatically:
- Discover your new example
- Detect API requirements
- Categorize by folder
- Include in test suite
