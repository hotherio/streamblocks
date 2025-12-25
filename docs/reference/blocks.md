# Blocks

Block type definitions and models.

## Core Models

### Block

The main block model representing extracted content:

```python
from hother.streamblocks.core.models import Block

block = Block(
    block_type="message",
    metadata={"author": "assistant"},
    content="Hello, how can I help you?"
)

# Access properties
print(block.block_type)  # "message"
print(block.content)     # "Hello, how can I help you?"
print(block.metadata)    # {"author": "assistant"}
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

## Block Types

Streamblocks supports various block types for different content:

### Message Blocks

For text messages and responses:

```python
block = Block(
    block_type="message",
    metadata={"author": "assistant"},
    content="Hello, how can I help you?"
)
```

### Tool Call Blocks

For function/tool invocations:

```python
block = Block(
    block_type="tool_call",
    metadata={"name": "search", "id": "call_123"},
    content='{"query": "weather today"}'
)
```

### Code Blocks

For code snippets:

```python
block = Block(
    block_type="code",
    metadata={"language": "python"},
    content="print('Hello, World!')"
)
```

## Custom Block Types

Define custom block types for your application:

```python
from hother.streamblocks.core.models import Block

class ConfigBlock(Block):
    block_type = "config"

    def validate(self) -> bool:
        import json
        try:
            json.loads(self.content)
            return True
        except json.JSONDecodeError:
            return False
```

## API Reference

::: hother.streamblocks.core.models
    options:
      show_root_heading: true
      show_source: false
