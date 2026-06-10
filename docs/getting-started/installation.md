# Installation

StreamBlocks requires **Python 3.13 or later**.

```bash
pip install streamblocks
```

!!! note "Package name vs. import name"
    The package is installed as `streamblocks` but imported from the `hother` namespace:

    ```python
    from hother.streamblocks import Registry, StreamBlockProcessor
    ```

## Provider extras

The core library has no provider dependencies. Install extras for the providers you use:

```bash
pip install streamblocks[all-providers]
```

| Extra | Enables |
|-------|---------|
| `gemini` | Google Gemini input adapter (`google-genai`) |
| `openai` | OpenAI input adapter (`openai`) |
| `anthropic` | Anthropic Claude input adapter (`anthropic`) |
| `all-providers` | All of the above |
| `structlog` | [structlog](https://www.structlog.org/) logging integration |
| `loguru` | [Loguru](https://loguru.readthedocs.io/) logging integration |
| `examples` | Dependencies for running the bundled examples |

## Development install

To work on StreamBlocks itself or run the examples from a clone:

```bash
git clone https://github.com/hotherio/streamblocks.git
cd streamblocks
uv sync --all-groups
```

## Next step

Continue with the [Quickstart](quickstart.md).
