# Examples

Runnable examples organized as a progressive learning path, from minimal quickstarts to full provider demos. All examples live in [`src/hother/streamblocks_examples/`](https://github.com/hotherio/streamblocks/tree/main/src/hother/streamblocks_examples) and are rendered in full on the pages below.

## Learning path

| Category | Description |
|----------|-------------|
| [00_quickstart](quickstart.md) | Ultra-minimal examples (~40-50 lines); start here |
| [01_basics](basics.md) | Core concepts: processing, errors, structured output, validators |
| [02_syntaxes](syntaxes.md) | Block syntax formats: markdown, delimiter, decorators, custom syntaxes |
| [03_adapters](adapters.md) | Input/output adapters for provider streams and event handling |
| [04_blocks](blocks.md) | Concrete block types: patches, tool calls, memory, visualizations |
| 05_logging | Logging integration, covered in the [Logging guide](../guides/logging.md) |
| [06_integrations](integrations.md) | Framework integrations: Pydantic AI, AG-UI |
| [07_providers](providers.md) | End-to-end AI provider demos (Gemini) |
| 08_ui | Interactive Textual TUI examples; run locally (see [Providers](providers.md#interactive-ui-examples-08_ui)) |
| 09_advanced | Performance tuning, covered in the [Performance guide](../guides/performance.md) |

The repository also ships supporting packages used throughout the examples:

- [`blocks/`](https://github.com/hotherio/streamblocks/tree/main/src/hother/streamblocks_examples/blocks): a reusable library of block definitions (file operations, patches, tool calls, memory, visualizations, interactive blocks).
- [`helpers/`](https://github.com/hotherio/streamblocks/tree/main/src/hother/streamblocks_examples/helpers): stream simulators and event handlers.
- [`tools/`](https://github.com/hotherio/streamblocks/tree/main/src/hother/streamblocks_examples/tools): tool implementations used by agent-style demos.

## Running examples

Run any example directly:

```bash
uv run python src/hother/streamblocks_examples/00_quickstart/01_hello_world.py
```

### Example runner

A runner script executes all examples with filtering and reporting:

```bash
uv run python -m hother.streamblocks_examples.run_examples [OPTIONS]
```

| Flag | Description |
|------|-------------|
| `--category <name>` | Run only examples from a specific category (e.g. `03_adapters`) |
| `--skip-api` | Skip examples that require API keys |
| `--include-ui` | Include TUI examples (they will likely fail without interaction) |
| `--dry-run` | Show what would be executed without running |
| `--parallel` | Run examples in parallel (faster but harder to debug) |
| `--timeout <seconds>` | Timeout per example (default: 30) |
| `--verbose`, `-v` | Show stdout/stderr for all examples, not just failures |
| `--output <text\|json>` | Output format: colored text (default) or machine-readable JSON |

A common invocation that needs no API keys:

```bash
uv run python -m hother.streamblocks_examples.run_examples --skip-api
```

## API keys

Most examples run offline against simulated streams. Provider-backed examples need one of the following environment variables:

| Provider | Environment variable | Where to get a key |
|----------|---------------------|--------------------|
| Google Gemini | `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) | <https://aistudio.google.com/apikey> |
| OpenAI | `OPENAI_API_KEY` | <https://platform.openai.com/api-keys> |
| Anthropic | `ANTHROPIC_API_KEY` | <https://console.anthropic.com/settings/keys> |

```bash
export GEMINI_API_KEY="your-key-here"  # pragma: allowlist secret
```

Each example page notes which keys it requires.

## Logging and performance examples

The `05_logging` and `09_advanced` examples are not duplicated here; they are embedded in their respective guides: see the [Logging guide](../guides/logging.md) and the [Performance guide](../guides/performance.md).
