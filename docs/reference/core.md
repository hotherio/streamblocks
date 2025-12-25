# Core Components

Core Streamblocks components and the main processor.

## StreamBlockProcessor

The main processing engine for extracting blocks from streams.

```python
from hother.streamblocks import StreamBlockProcessor

processor = StreamBlockProcessor(
    syntaxes=[MarkdownFrontmatterSyntax()],
    emit_text_delta=True,
    emit_block_events=True,
)

async for event in processor.process_stream(stream):
    print(event)
```

## Event Types

### EventType

Event type enumeration:

- `TEXT_DELTA` - Raw text chunk from the stream
- `BLOCK_OPENED` - A new block was detected
- `BLOCK_UPDATED` - Block content was updated
- `BLOCK_CLOSED` - Block parsing completed
- `NATIVE_EVENT` - Provider-specific event (passthrough)

### BlockState

Block state enumeration:

- `OPEN` - Block is currently being parsed
- `CLOSED` - Block parsing is complete
- `ERROR` - Block parsing encountered an error

## Models

### Block

The main block model:

```python
from hother.streamblocks.core.models import Block

block = Block(
    block_type="message",
    metadata={"author": "assistant"},
    content="Hello, World!"
)
```

### BlockCandidate

Represents a potential block during parsing:

```python
from hother.streamblocks.core.models import BlockCandidate

candidate = BlockCandidate(
    syntax=syntax,
    start_line=1,
)
```

## API Reference

::: hother.streamblocks.core.types
    options:
      show_root_heading: true
      show_source: false

::: hother.streamblocks.core.models
    options:
      show_root_heading: true
      show_source: false
