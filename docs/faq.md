# Frequently Asked Questions

Common questions about Streamblocks.

## General

### What is Streamblocks?

Streamblocks is a Python library for extracting structured blocks from text streams in real-time. It's designed to work with LLM output streams, enabling reactive applications that process content as it's generated.

### How is this different from just parsing JSON?

Streamblocks extracts blocks **while streaming**, not after completion. This enables:

- **Real-time reactions** - Respond to content immediately
- **Feedback loops** - Provide input to LLMs mid-generation
- **Progress tracking** - Show users what's happening
- **Early termination** - Stop processing when needed

JSON parsing requires waiting for the complete response.

### What LLM providers are supported?

Streamblocks includes adapters for:

- **Google Gemini** - `streamblocks[gemini]`
- **OpenAI** - `streamblocks[openai]`
- **Anthropic Claude** - `streamblocks[anthropic]`

Any text stream can be processed—adapters just normalize the format.

### Can I use Streamblocks with LangChain/LangGraph?

Yes! Streamblocks is framework-agnostic. Process any text stream:

```python
# Works with any async iterator
async for event in processor.process_stream(langchain_stream):
    ...
```

## Blocks & Syntaxes

### What block formats are supported?

Three built-in syntaxes:

1. **Delimiter Preamble** - `!!id:type\ncontent\n!!end`
2. **Delimiter Frontmatter** - YAML frontmatter with delimiters
3. **Markdown Frontmatter** - Code fences with YAML frontmatter

You can also create [custom syntaxes](syntaxes.md).

### Can I define custom block types?

Yes! Create Pydantic models for metadata and content:

```python
from streamblocks import Block, BaseMetadata, BaseContent

class TaskMetadata(BaseMetadata):
    block_type: Literal["task"] = "task"
    priority: str = "normal"

class TaskContent(BaseContent):
    @classmethod
    def parse(cls, raw_text: str) -> "TaskContent":
        return cls(raw_content=raw_text)

class Task(Block[TaskMetadata, TaskContent]):
    pass
```

### How do I handle malformed blocks?

Malformed blocks emit `BLOCK_REJECTED` events:

```python
async for event in processor.process_stream(stream):
    if event.type == EventType.BLOCK_REJECTED:
        print(f"Rejected: {event.rejection.reason}")
```

## Performance

### What's the performance overhead?

Streamblocks adds minimal overhead:

- Line-by-line processing with efficient buffering
- No regex compilation per-line (patterns are pre-compiled)
- Async-native design for non-blocking I/O

For most applications, the LLM API latency dominates.

### Can I process multiple streams concurrently?

Yes, each `StreamBlockProcessor` instance is independent:

```python
async def process_multiple():
    processors = [StreamBlockProcessor(registry, syntax) for _ in range(3)]
    tasks = [process_stream(p, stream) for p, stream in zip(processors, streams)]
    await asyncio.gather(*tasks)
```

## Troubleshooting

### Blocks aren't being detected

1. **Check syntax** - Ensure block format matches the configured syntax
2. **Check delimiters** - Verify start/end markers are correct
3. **Enable logging** - Use `DEBUG` level to see processing details

```python
import logging
logging.getLogger("streamblocks").setLevel(logging.DEBUG)
```

### Import errors

Install the appropriate extras:

```bash
uv add streamblocks[gemini]   # For Gemini
uv add streamblocks[openai]   # For OpenAI
uv add streamblocks[anthropic]  # For Anthropic
```

### Type errors with Pydantic

Ensure your metadata/content classes inherit correctly:

```python
from streamblocks import BaseMetadata, BaseContent

class MyMetadata(BaseMetadata):  # Must inherit BaseMetadata
    ...

class MyContent(BaseContent):   # Must inherit BaseContent
    ...
```

## More Help

- [Troubleshooting Guide](troubleshooting.md) - Detailed solutions
- [Community](community.md) - Get help from the community
- [GitHub Issues](https://github.com/hotherio/streamblocks/issues) - Report bugs
