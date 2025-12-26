# Examples Setup

This guide explains how to set up and run the Streamblocks examples.

## Prerequisites

- Python 3.11+
- uv (recommended) or pip

## Installation

### Clone the Repository

```bash
git clone https://github.com/hotherio/streamblocks.git
cd streamblocks
```

### Install Dependencies

=== "uv"
    ```bash
    uv sync --all-extras
    ```

=== "pip"
    ```bash
    pip install -e ".[dev,gemini,openai,anthropic]"
    ```

## Running Examples

### Quick Start

Run all standalone examples (no API keys required):

```bash
uv run python examples/run_examples.py --skip-api
```

### With API Keys

Set your API keys and run all examples:

```bash
export GEMINI_API_KEY="your-key-here"  # pragma: allowlist secret
export OPENAI_API_KEY="your-key-here"  # pragma: allowlist secret
export ANTHROPIC_API_KEY="your-key-here"  # pragma: allowlist secret

uv run python examples/run_examples.py
```

### Runner Options

```bash
# Run specific category
uv run python examples/run_examples.py --category adapters

# Dry run (see what would execute)
uv run python examples/run_examples.py --dry-run

# Verbose output
uv run python examples/run_examples.py --verbose

# Run in parallel (faster)
uv run python examples/run_examples.py --parallel

# Custom timeout
uv run python examples/run_examples.py --timeout 60

# JSON output
uv run python examples/run_examples.py --output json
```

### Run Individual Examples

```bash
# Basic example (no API key)
uv run python examples/01_basics/01_basic_usage.py

# Gemini example (requires API key)
export GEMINI_API_KEY="your-key-here"  # pragma: allowlist secret
uv run python examples/03_adapters/02_gemini_auto_detect.py
```

## API Keys

### Google Gemini

```bash
export GEMINI_API_KEY="your-key-here"  # pragma: allowlist secret
# or
export GOOGLE_API_KEY="your-key-here"  # pragma: allowlist secret
```

Get your key: [Google AI Studio](https://aistudio.google.com/apikey)

### OpenAI

```bash
export OPENAI_API_KEY="your-key-here"  # pragma: allowlist secret
```

Get your key: [OpenAI Platform](https://platform.openai.com/api-keys)

### Anthropic

```bash
export ANTHROPIC_API_KEY="your-key-here"  # pragma: allowlist secret
```

Get your key: [Anthropic Console](https://console.anthropic.com/settings/keys)

## Example Categories

| Directory | Description | Requires API |
|-----------|-------------|--------------|
| `01_basics/` | Core concepts | No |
| `02_syntaxes/` | Syntax formats | No |
| `03_adapters/` | Provider adapters | Some |
| `04_logging/` | Logging options | No |
| `05_ui/` | UI examples | No |
| `06_integrations/` | Framework integrations | Some |

## Pytest Integration

Run examples as tests:

```bash
# Run all
pytest tests/test_examples.py

# Skip API examples
pytest tests/test_examples.py -m "not api"

# Skip UI examples
pytest tests/test_examples.py -m "not ui"

# Verbose
pytest tests/test_examples.py -v
```

## Troubleshooting

### Timeout Issues

Increase the timeout:

```bash
uv run python examples/run_examples.py --timeout 120
```

### Rate Limits

Run sequentially instead of parallel:

```bash
uv run python examples/run_examples.py
```

### Import Errors

Reinstall with all extras:

```bash
uv sync --all-extras
```

## Next Steps

- [Basic Examples](basic.md) - Start here
- [Adapter Examples](adapters.md) - Provider integration
- [Integration Examples](integrations.md) - Framework usage
