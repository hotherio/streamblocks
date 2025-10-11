# StreamBlocks Examples

This directory contains example scripts demonstrating various features of StreamBlocks.

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
uv run python examples/run_examples.py --category adapters

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
      "path": "examples/adapters/01_identity_adapter_plain_text.py",
      "status": "pass",
      "category": "adapters",
      "duration": 0.82
    }
  ],
  "skipped": [
    {
      "path": "examples/ui/interactive_ui_demo.py",
      "reason": "TUI example (requires user interaction)",
      "category": "ui"
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

### Adapters (`adapters/`)

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

### Integrations (`integrations/`)

Examples showing integration with other libraries:

- `pydantic_ai_integration.py` - **Requires API keys** - PydanticAI integration

### Logging (`logging/`)

Examples demonstrating different logging approaches:

- `custom_logger_example.py` - Custom logger implementation
- `stdlib_logging_example.py` - Python stdlib logging
- `structlog_example.py` - Structured logging with structlog

### Syntaxes (`syntaxes/`)

Examples showing different syntax formats:

- `delimiter_frontmatter_example.py` - Delimiter with frontmatter syntax
- `markdown_frontmatter_example.py` - Markdown frontmatter syntax

### UI (`ui/`)

User interface examples:

- `interactive_blocks_example.py` - Interactive block types (CLI output)
- `interactive_ui_demo.py` - **TUI - Cannot run automatically** - Full Textual UI demo

### Root Examples

Core examples in the root directory:

- `basic_usage.py` - Basic StreamBlocks usage
- `error_handling_example.py` - Error handling patterns
- `gemini_simple_demo.py` - **Requires GEMINI_API_KEY** - Simple Gemini demo
- `gemini_architect_example.py` - **Requires GEMINI_API_KEY** - Complex Gemini example
- `minimal_api_example.py` - Minimal API example
- `parsing_decorators_example.py` - Using parsing decorators
- `patch_content_example.py` - Patch content operations
- `structured_output_example.py` - Structured output handling

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
uv run python examples/basic_usage.py

# API example (requires key)
export GEMINI_API_KEY="your-key-here"
uv run python examples/gemini_simple_demo.py
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

1. **Place in appropriate category folder** - adapters, integrations, logging, etc.
2. **Add docstring** - Explain what the example demonstrates
3. **Document requirements** - Note any API keys or special dependencies
4. **Follow naming convention** - Use descriptive names (e.g., `12_feature_name.py`)
5. **Make it runnable** - Include `if __name__ == "__main__":` block
6. **Test it** - Run with `uv run python examples/run_examples.py` to verify

The runner will automatically:
- Discover your new example
- Detect API requirements
- Categorize by folder
- Include in test suite
