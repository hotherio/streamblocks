# Provider Examples

Examples for working with different LLM providers.

## Google Gemini

### Basic Usage

```python
import asyncio
import google.generativeai as genai
from streamblocks import StreamBlockProcessor, BlockRegistry, Syntax, EventType

async def gemini_example():
    genai.configure(api_key="your-api-key")  # pragma: allowlist secret  # pragma: allowlist secret
    model = genai.GenerativeModel("gemini-pro")

    prompt = """
    Create a task list:

    !!task01:task
    Review code changes
    !!end

    !!task02:task
    Update documentation
    !!end
    """

    response = model.generate_content(prompt, stream=True)

    processor = StreamBlockProcessor(
        registry=BlockRegistry(),
        syntax=Syntax.DELIMITER_PREAMBLE,
        input_adapter="auto",
    )

    async for event in processor.process_stream(response):
        if event.type == EventType.BLOCK_EXTRACTED:
            print(f"Task: {event.block.content.raw_content}")

asyncio.run(gemini_example())
```

### With Explicit Adapter

```python
from streamblocks.ext.gemini import GeminiInputAdapter

processor = StreamBlockProcessor(
    registry=BlockRegistry(),
    syntax=Syntax.DELIMITER_PREAMBLE,
    input_adapter=GeminiInputAdapter(),
)
```

## OpenAI

### Basic Usage

```python
import asyncio
from openai import OpenAI
from streamblocks import StreamBlockProcessor, BlockRegistry, Syntax, EventType
from streamblocks.ext.openai import OpenAIInputAdapter

async def openai_example():
    client = OpenAI(api_key="your-api-key")  # pragma: allowlist secret

    prompt = """
    Create a task list using:
    !!id:task
    description
    !!end
    """

    stream = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        stream=True,
    )

    processor = StreamBlockProcessor(
        registry=BlockRegistry(),
        syntax=Syntax.DELIMITER_PREAMBLE,
        input_adapter=OpenAIInputAdapter(),
    )

    async for event in processor.process_stream(stream):
        if event.type == EventType.BLOCK_EXTRACTED:
            print(f"Task: {event.block.content.raw_content}")

asyncio.run(openai_example())
```

### Streaming Text Display

```python
processor = StreamBlockProcessor(
    registry=BlockRegistry(),
    syntax=Syntax.DELIMITER_PREAMBLE,
    input_adapter=OpenAIInputAdapter(),
    emit_text_deltas=True,
)

async for event in processor.process_stream(stream):
    match event.type:
        case EventType.TEXT_DELTA:
            print(event.text, end="", flush=True)
        case EventType.BLOCK_EXTRACTED:
            print(f"\n[Block: {event.block.metadata.id}]")
```

## Anthropic

### Basic Usage

```python
import asyncio
import anthropic
from streamblocks import StreamBlockProcessor, BlockRegistry, Syntax, EventType
from streamblocks.ext.anthropic import AnthropicInputAdapter

async def anthropic_example():
    client = anthropic.Anthropic(api_key="your-api-key")  # pragma: allowlist secret

    prompt = """
    Create a task list using:
    !!id:task
    description
    !!end
    """

    processor = StreamBlockProcessor(
        registry=BlockRegistry(),
        syntax=Syntax.DELIMITER_PREAMBLE,
        input_adapter=AnthropicInputAdapter(),
    )

    with client.messages.stream(
        model="claude-3-opus",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        async for event in processor.process_stream(stream):
            if event.type == EventType.BLOCK_EXTRACTED:
                print(f"Task: {event.block.content.raw_content}")

asyncio.run(anthropic_example())
```

## Plain Text Streams

### Identity Adapter

For plain text without LLM-specific formatting:

```python
from streamblocks.adapters import IdentityAdapter

async def plain_text_stream():
    yield "!!task01:task\n"
    yield "Do something\n"
    yield "!!end\n"

processor = StreamBlockProcessor(
    registry=BlockRegistry(),
    syntax=Syntax.DELIMITER_PREAMBLE,
    input_adapter=IdentityAdapter(),
)

async for event in processor.process_stream(plain_text_stream()):
    if event.type == EventType.BLOCK_EXTRACTED:
        print(event.block)
```

### No Adapter

Strings work directly:

```python
async def string_stream():
    yield "!!task01:task\nDo something\n!!end\n"

async for event in processor.process_stream(string_stream()):
    if event.type == EventType.BLOCK_EXTRACTED:
        print(event.block)
```

## Auto-Detection

Let Streamblocks detect the provider:

```python
processor = StreamBlockProcessor(
    registry=BlockRegistry(),
    syntax=Syntax.DELIMITER_PREAMBLE,
    input_adapter="auto",  # Detects from first event
)

# Works with any supported provider
async for event in processor.process_stream(any_stream):
    handle_event(event)
```

## Error Handling

### Provider Errors

```python
import google.api_core.exceptions

try:
    async for event in processor.process_stream(gemini_stream):
        handle_event(event)
except google.api_core.exceptions.ResourceExhausted:
    print("Rate limit exceeded")
    await asyncio.sleep(60)
except google.api_core.exceptions.InvalidArgument as e:
    print(f"Invalid request: {e}")
```

### Block Rejections

```python
async for event in processor.process_stream(stream):
    if event.type == EventType.BLOCK_REJECTED:
        print(f"Block rejected: {event.rejection.reason}")
    elif event.type == EventType.BLOCK_EXTRACTED:
        print(f"Block extracted: {event.block.metadata.id}")
```

## Next Steps

- [Basic Examples](basic.md) - Core concepts
- [Adapter Examples](adapters.md) - Adapter details
- [Integration Examples](integrations.md) - Framework usage
