# Getting Started

This guide will help you get up and running with StreamBlocks in just a few minutes.

## Quick Example

Here's a minimal example showing how to process a text stream and extract structured blocks:

```python
import asyncio
from hother.streamblocks import StreamBlockProcessor
from hother.streamblocks.syntaxes import MarkdownFrontmatterSyntax

async def main():
    # Create a processor with markdown frontmatter syntax
    processor = StreamBlockProcessor(
        syntaxes=[MarkdownFrontmatterSyntax()]
    )

    # Simulate a text stream
    text_chunks = [
        "# Hello World\n",
        "---\n",
        "type: message\n",
        "---\n",
        "This is the content.\n",
    ]

    # Process the stream
    async for event in processor.process_stream(iter(text_chunks)):
        print(f"Event: {event.type} - {event}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Core Concepts

### Blocks

A **block** is a structured unit of content extracted from a text stream. Blocks have:

- **Type**: What kind of content it contains (message, code, tool call, etc.)
- **Metadata**: Key-value pairs describing the block
- **Content**: The actual content of the block

### Syntaxes

**Syntaxes** define how blocks are detected and parsed from text streams. StreamBlocks provides several built-in syntaxes:

- `MarkdownFrontmatterSyntax`: Blocks with YAML frontmatter
- `DelimiterFrontmatterSyntax`: Blocks with custom delimiters
- `FencedCodeSyntax`: Markdown code blocks

### Events

The processor emits **events** as it processes the stream:

- `TEXT_DELTA`: Raw text chunks
- `BLOCK_OPENED`: A new block was detected
- `BLOCK_UPDATED`: Block content was updated
- `BLOCK_CLOSED`: Block parsing completed

## Next Steps

- [Basics](basics.md) - Learn core concepts in depth
- [Examples](examples/index.md) - Explore working examples
- [API Reference](reference/index.md) - Detailed API documentation
