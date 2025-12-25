# Core Concepts

This guide covers the fundamental concepts of Streamblocks.

## Block Model

A block represents a structured unit of content extracted from a text stream.

```python
from hother.streamblocks.core.models import Block

# Blocks have these key attributes:
# - block_type: The type of block (e.g., "message", "code", "tool_call")
# - metadata: Dictionary of key-value pairs
# - content: The actual content string
# - state: Current parsing state (OPEN, CLOSED, etc.)
```

## Syntaxes

Syntaxes define the rules for detecting and parsing blocks from text.

### Built-in Syntaxes

#### MarkdownFrontmatterSyntax

Parses blocks with YAML frontmatter between `---` delimiters:

```markdown
---
type: message
author: assistant
---
This is the message content.
```

#### DelimiterFrontmatterSyntax

Uses custom delimiters for block boundaries:

```text
<<<BLOCK
type: code
language: python
>>>
def hello():
    print("Hello, World!")
<<<END>>>
```

### Custom Syntaxes

You can create custom syntaxes by extending `BaseSyntax`:

```python
from hother.streamblocks.syntaxes.base import BaseSyntax

class MySyntax(BaseSyntax):
    def detect_start(self, line: str) -> bool:
        return line.startswith("[[START]]")

    def detect_end(self, line: str) -> bool:
        return line.startswith("[[END]]")

    def parse_metadata(self, content: str) -> dict:
        return {"type": "custom"}
```

## Stream Processing

The `StreamBlockProcessor` handles the main processing loop:

```python
from hother.streamblocks import StreamBlockProcessor

processor = StreamBlockProcessor(
    syntaxes=[MarkdownFrontmatterSyntax()],
    emit_text_delta=True,  # Emit raw text events
    emit_block_events=True,  # Emit block lifecycle events
)

async for event in processor.process_stream(stream):
    match event.type:
        case EventType.TEXT_DELTA:
            print(f"Text: {event.data}")
        case EventType.BLOCK_OPENED:
            print(f"Block started: {event.block.block_type}")
        case EventType.BLOCK_CLOSED:
            print(f"Block finished: {event.block.content}")
```

## Event Types

Streamblocks emits these event types:

| Event | Description |
|-------|-------------|
| `TEXT_DELTA` | Raw text chunk from the stream |
| `BLOCK_OPENED` | A new block was detected |
| `BLOCK_UPDATED` | Block content was updated |
| `BLOCK_CLOSED` | Block parsing completed |
| `NATIVE_EVENT` | Provider-specific event (passthrough) |

## Adapters

Adapters transform provider-specific stream formats into text chunks:

```python
from hother.streamblocks.adapters import GeminiAdapter

# Wrap a Gemini stream
adapted_stream = GeminiAdapter()(gemini_response)

# Process the adapted stream
async for event in processor.process_stream(adapted_stream):
    ...
```

See [Advanced Usage](advanced.md) for more on adapters.
