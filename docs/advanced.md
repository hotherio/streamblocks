# Advanced Usage

This guide covers advanced Streamblocks features and patterns.

## Stream Adapters

Adapters convert provider-specific stream formats into text chunks that Streamblocks can process.

### Built-in Adapters

#### GeminiAdapter

For Google Gemini streams:

```python
from hother.streamblocks.adapters import GeminiAdapter
from google import genai

client = genai.Client()
response = client.models.generate_content_stream(
    model="gemini-2.0-flash-exp",
    contents="Write a hello world function"
)

# Adapt the stream
adapter = GeminiAdapter()
async for event in processor.process_stream(adapter(response)):
    ...
```

#### OpenAIAdapter

For OpenAI streams:

```python
from hother.streamblocks.adapters import OpenAIAdapter
from openai import OpenAI

client = OpenAI()
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello"}],
    stream=True
)

adapter = OpenAIAdapter()
async for event in processor.process_stream(adapter(response)):
    ...
```

#### AnthropicAdapter

For Anthropic streams:

```python
from hother.streamblocks.adapters import AnthropicAdapter
from anthropic import Anthropic

client = Anthropic()
with client.messages.stream(...) as stream:
    adapter = AnthropicAdapter()
    async for event in processor.process_stream(adapter(stream)):
        ...
```

### Auto-Detection

Streamblocks can automatically detect the appropriate adapter:

```python
from hother.streamblocks.adapters import auto_detect_adapter

adapter = auto_detect_adapter(response)
if adapter:
    async for event in processor.process_stream(adapter(response)):
        ...
```

### Custom Adapters

Create custom adapters for other providers:

```python
from hother.streamblocks.adapters.base import BaseAdapter

class MyProviderAdapter(BaseAdapter):
    def __call__(self, stream):
        for chunk in stream:
            # Extract text from provider-specific format
            yield chunk.text
```

## Parsing Decorators

Use decorators to add parsing logic to blocks:

```python
from hother.streamblocks.core.parsing import parser, json_parser

@parser("json")
def parse_json_block(content: str) -> dict:
    import json
    return json.loads(content)

@json_parser
def parse_config(content: dict) -> Config:
    return Config(**content)
```

## Custom Block Types

Define custom block types for your application:

```python
from hother.streamblocks.blocks import MessageBlock, ToolCallBlock

# Built-in block types
class MessageBlock:
    block_type = "message"
    content: str
    author: str

class ToolCallBlock:
    block_type = "tool_call"
    name: str
    arguments: dict
```

## Logging Integration

Streamblocks supports multiple logging backends:

### stdlib logging

```python
import logging
from hother.streamblocks import StreamBlockProcessor

logging.basicConfig(level=logging.DEBUG)
processor = StreamBlockProcessor(logger=logging.getLogger("streamblocks"))
```

### structlog

```python
import structlog
from hother.streamblocks import StreamBlockProcessor

logger = structlog.get_logger("streamblocks")
processor = StreamBlockProcessor(logger=logger)
```

## Error Handling

Handle parsing errors gracefully:

```python
from hother.streamblocks.core.types import EventType

async for event in processor.process_stream(stream):
    if event.type == EventType.ERROR:
        print(f"Error: {event.error}")
        continue
    # Process other events...
```

## Performance Considerations

For high-throughput scenarios:

- Use `emit_text_delta=False` if you only need blocks
- Use appropriate buffer sizes
- Consider async processing for I/O-bound operations

See [Performance](performance.md) for detailed optimization tips.
