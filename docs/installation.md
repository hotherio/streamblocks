# Installation

StreamBlocks can be installed using pip or uv.

## Basic Installation

```bash
pip install streamblocks
```

## With AI Provider Support

Install with specific AI provider support:

```bash
# Gemini support
pip install streamblocks[gemini]

# OpenAI support
pip install streamblocks[openai]

# Anthropic support
pip install streamblocks[anthropic]

# All providers
pip install streamblocks[all-providers]
```

## With Enhanced Logging

```bash
# Structlog integration
pip install streamblocks[structlog]

# Loguru integration
pip install streamblocks[loguru]
```

## Development Installation

For development, clone the repository and install with all dependencies:

```bash
git clone https://github.com/hotherio/streamblocks.git
cd streamblocks
uv sync --all-extras
```

## Requirements

- Python 3.13 or higher
- pydantic >= 2.0
- pyyaml >= 6.0

## Verifying Installation

```python
from hother.streamblocks import StreamBlockProcessor

print("StreamBlocks installed successfully!")
```
