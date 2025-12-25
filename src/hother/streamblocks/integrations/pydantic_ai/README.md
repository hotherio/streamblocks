# PydanticAI Integration for Streamblocks

This integration allows PydanticAI agents to transparently generate Streamblocks-compatible output that is extracted and processed in real-time during streaming.

## Installation

```bash
pip install pydantic-ai
```

## Key Features

- **Transparent Integration**: PydanticAI agents generate text streams with embedded blocks
- **Real-time Extraction**: Blocks are extracted and emitted as the agent streams
- **Registry-based Instructions**: Agent system prompts are automatically enhanced with block formats from the registry
- **Type Safety**: Full Pydantic validation throughout the pipeline
- **100% Compatible**: Works with standard PydanticAI Agent interface

## Architecture

```
User Prompt → PydanticAI Agent → Text Stream → Streamblocks Processor → Events
                    ↑                                                      ↓
            Registry (block formats)                        Extracted Blocks + Raw Text
```

## Components

### BlockAwareAgent

A wrapper around PydanticAI Agent that automatically configures it with Streamblocks syntax knowledge:

```python
from streamblocks import Registry, DelimiterPreambleSyntax
from streamblocks.integrations.pydantic_ai import BlockAwareAgent

# Setup registry with syntaxes
syntax = DelimiterPreambleSyntax(...)
registry = Registry(syntax)

# Create block-aware agent
agent = BlockAwareAgent(
    model='openai:gpt-4o',
    registry=registry,
)

# Agent now knows about block formats!
async for event in agent.run_with_blocks("Create a Python project"):
    if event.type == EventType.BLOCK_EXTRACTED:
        # Process extracted block
        pass
```

### AgentStreamProcessor

Enhanced processor optimized for PydanticAI agent streaming output:

```python
from streamblocks.integrations.pydantic_ai import AgentStreamProcessor

processor = AgentStreamProcessor(registry)

# Process agent stream
async for event in processor.process_agent_stream(agent_stream):
    # Handle events
    pass
```

### RegistryToPrompt

Converts Streamblocks registry definitions into agent instructions:

```python
from streamblocks.integrations.pydantic_ai import RegistryToPrompt

prompt_generator = RegistryToPrompt(registry)
instructions = prompt_generator.generate_instructions()
# Returns formatted instructions about available block formats
```

## Usage Examples

### Basic Example: Block-Aware Agent

```python
import asyncio
from streamblocks import Registry, DelimiterPreambleSyntax, EventType
from streamblocks.content import FileOperationsContent, FileOperationsMetadata
from streamblocks.integrations.pydantic_ai import BlockAwareAgent

async def main():
    # Setup registry
    syntax = DelimiterPreambleSyntax(
        name="files_operations_syntax",
        metadata_class=FileOperationsMetadata,
        content_class=FileOperationsContent,
    )
    registry = Registry(syntax)

    # Create block-aware agent
    agent = BlockAwareAgent(
        model='openai:gpt-4o',
        registry=registry,
    )

    # Run agent with block extraction
    async for event in agent.run_with_blocks("Create a Python web API"):
        if event.type == EventType.BLOCK_EXTRACTED:
            block = event.metadata["extracted_block"]
            print(f"Block: {block.metadata.id}")
            for op in block.content.operations:
                print(f"  - {op.action}: {op.path}")

asyncio.run(main())
```

### Advanced Example: Standard Agent + Processor

```python
from pydantic_ai import Agent
from streamblocks.integrations.pydantic_ai import AgentStreamProcessor

# Use standard PydanticAI agent
agent = Agent(
    'openai:gpt-4o',
    system_prompt="Use !!id:type format for structured blocks..."
)

# Process with Streamblocks
processor = AgentStreamProcessor(registry)

async with agent.run_stream(prompt) as result:
    async def stream():
        async for text in result.stream_text():
            yield text

    async for event in processor.process_agent_stream(stream()):
        # Handle events
        pass
```

## How It Works

1. **Registry Analysis**: The integration analyzes the Streamblocks registry to understand available block formats
2. **Prompt Enhancement**: Agent system prompts are automatically enhanced with instructions about block formats
3. **Streaming Generation**: Agent generates text with embedded blocks using the learned formats
4. **Real-time Extraction**: Streamblocks processor extracts blocks as they appear in the stream
5. **Event Emission**: Both raw text and extracted blocks are emitted as events

## Block Format Instructions

When a registry is provided, the agent receives instructions like:

```
You can use the following block formats in your responses:

1. Block with inline metadata using !! delimiter
   Format: !!<id>:<type>[:param1:param2...]
   content
   !!end
   Parameters: id, type, additional parameters

When creating structured content, use these block formats.
The blocks will be automatically extracted and processed.
```

## Compatibility

- Works with all PydanticAI-supported models (OpenAI, Anthropic, Google, etc.)
- Compatible with all Streamblocks syntaxes
- Supports both sync and async operations
- Full streaming support with partial block updates

## Best Practices

1. **Use Specific Syntaxes**: Define syntaxes that match your use case
2. **Validate Blocks**: Add validators to the registry for business logic
3. **Handle Events**: Process both BLOCK_EXTRACTED and RAW_TEXT events
4. **Stream Processing**: Use BLOCK_DELTA events for real-time updates
5. **Error Handling**: Handle BLOCK_REJECTED events gracefully

## Examples

See `examples/pydantic_ai_integration.py` for complete working examples.
