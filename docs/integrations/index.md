# Integrations

StreamBlocks integrates with popular frameworks and libraries.

## Available Integrations

### [PydanticAI](pydantic_ai.md)

Integration with PydanticAI for building AI agents with structured responses.

- Process agent responses as structured blocks
- Handle tool calls and messages
- Real-time streaming support

## Coming Soon

- **LangChain**: Chain-based workflows
- **FastAPI**: Web application streaming
- **LlamaIndex**: Document processing

## Creating Custom Integrations

StreamBlocks is designed to be easily integrated with other tools. The core `StreamBlockProcessor` can wrap any async iterator:

```python
from hother.streamblocks import StreamBlockProcessor

async def process_custom_stream(stream):
    processor = StreamBlockProcessor()
    async for event in processor.process_stream(stream):
        yield event
```

See [Advanced Usage](../advanced.md) for more details on custom integrations.
