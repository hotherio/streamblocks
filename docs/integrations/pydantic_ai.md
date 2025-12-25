# PydanticAI Integration

Streamblocks integrates with [PydanticAI](https://ai.pydantic.dev/) for processing structured agent responses.

## Installation

```bash
pip install streamblocks pydantic-ai
```

## Basic Usage

```python
from pydantic_ai import Agent
from hother.streamblocks.integrations.pydantic_ai import StreamblocksProcessor

# Create a PydanticAI agent
agent = Agent(
    model="gemini-2.0-flash-exp",
    system_prompt="You are a helpful assistant."
)

# Create the processor
processor = StreamblocksProcessor()

# Process agent responses
async def run_agent(prompt: str):
    async with agent.run_stream(prompt) as response:
        async for event in processor.process(response):
            if event.type == EventType.BLOCK_CLOSED:
                print(f"Block: {event.block.block_type}")
                print(f"Content: {event.block.content}")
```

## Features

### Structured Block Extraction

Extract structured blocks from agent responses:

```python
async for event in processor.process(response):
    match event.type:
        case EventType.BLOCK_OPENED:
            print(f"New block: {event.block.block_type}")
        case EventType.BLOCK_UPDATED:
            print(f"Content: {event.block.content[-50:]}")
        case EventType.BLOCK_CLOSED:
            handle_complete_block(event.block)
```

### Tool Call Handling

Handle tool calls from the agent:

```python
async for event in processor.process(response):
    if event.type == EventType.BLOCK_CLOSED:
        if event.block.block_type == "tool_call":
            name = event.block.metadata.get("name")
            args = event.block.content
            result = await execute_tool(name, args)
```

### Real-time Streaming

Display content as it streams:

```python
async for event in processor.process(response):
    if event.type == EventType.TEXT_DELTA:
        print(event.data, end="", flush=True)
```

## Example

See the full example:

#! examples/06_integrations/01_pydantic_ai_integration.py

## API Reference

::: hother.streamblocks.integrations.pydantic_ai
    options:
      show_root_heading: true
      show_source: true
