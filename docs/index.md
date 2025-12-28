# Streamblocks

**Real-time extraction of structured blocks from AI text streams**

Streamblocks is a Python library for detecting and extracting structured content blocks from streaming text. Extract semantic blocks as they stream—not after completion—enabling reactive AI agents and real-time processing.

<div class="grid cards" markdown>

-   :material-lightning-bolt:{ .lg .middle } **Stream Processing**

    ---

    Extract blocks in real-time as text streams, enabling immediate reactions and feedback loops with LLMs.

    [:octicons-arrow-right-24: Getting Started](getting_started.md)

-   :material-puzzle:{ .lg .middle } **Multiple Syntaxes**

    ---

    Choose from delimiter-based, Markdown frontmatter, or create custom syntaxes for your use case.

    [:octicons-arrow-right-24: Syntaxes Guide](syntaxes.md)

-   :material-connection:{ .lg .middle } **Provider Adapters**

    ---

    Works with Gemini, OpenAI, Anthropic out of the box. Easy to add custom adapters.

    [:octicons-arrow-right-24: Adapters Guide](adapters.md)

-   :material-shield-check:{ .lg .middle } **Type Safe**

    ---

    Full Pydantic model support with validation. Define your block metadata and content with type safety.

    [:octicons-arrow-right-24: Block Types](blocks.md)

</div>

## Quick Example

```python
import asyncio
from streamblocks import StreamBlockProcessor, BlockRegistry, Syntax

async def main():
    # Create registry and processor
    registry = BlockRegistry()
    processor = StreamBlockProcessor(registry, syntax=Syntax.DELIMITER_PREAMBLE)

    # Simulate a text stream
    async def text_stream():
        chunks = [
            "Here's the file operations:\n",
            "!!file01:files_operations\n",
            "src/main.py:C\n",
            "src/utils.py:E\n",
            "!!end\n",
            "Done!"
        ]
        for chunk in chunks:
            yield chunk

    # Process and react to blocks in real-time
    async for event in processor.process_stream(text_stream()):
        if event.type.name == "BLOCK_EXTRACTED":
            print(f"Extracted: {event.block.metadata.id}")

asyncio.run(main())
```

## Why Streamblocks?

| Feature | Benefit |
|---------|---------|
| **LLM Agnostic** | Works with any text stream—no vendor lock-in |
| **Real-time Processing** | React to blocks as they stream, don't wait for completion |
| **Type Safety** | Pydantic models for metadata and content validation |
| **Extensible** | Custom syntaxes, adapters, and block types |
| **Framework Compatible** | Integrates with LangGraph, Pydantic AI, and others |

## Installation

=== "uv"

    ```bash
    uv add streamblocks
    ```

=== "pip"

    ```bash
    pip install streamblocks
    ```

With provider support:

=== "uv"

    ```bash
    uv add streamblocks[gemini]      # Google Gemini
    uv add streamblocks[openai]      # OpenAI
    uv add streamblocks[anthropic]   # Anthropic Claude
    uv add streamblocks[all-providers]  # All providers
    ```

=== "pip"

    ```bash
    pip install streamblocks[gemini]
    pip install streamblocks[openai]
    pip install streamblocks[anthropic]
    pip install streamblocks[all-providers]
    ```

[Get Started :material-arrow-right:](getting_started.md){ .md-button .md-button--primary }
[View Examples](examples/index.md){ .md-button }

