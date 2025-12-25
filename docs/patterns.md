# Common Patterns

This guide covers common usage patterns with Streamblocks.

## Processing LLM Responses

The most common use case is extracting structured blocks from LLM responses:

```python
async def process_llm_response(response_stream):
    processor = StreamBlockProcessor(
        syntaxes=[MarkdownFrontmatterSyntax()]
    )

    blocks = []
    async for event in processor.process_stream(response_stream):
        if event.type == EventType.BLOCK_CLOSED:
            blocks.append(event.block)

    return blocks
```

## Real-time Block Updates

Display blocks as they're being streamed:

```python
async def stream_with_updates(stream):
    processor = StreamBlockProcessor(
        syntaxes=[MarkdownFrontmatterSyntax()],
        emit_block_events=True,
    )

    current_block = None
    async for event in processor.process_stream(stream):
        match event.type:
            case EventType.BLOCK_OPENED:
                current_block = event.block
                print(f"Started: {current_block.block_type}")
            case EventType.BLOCK_UPDATED:
                print(f"Content: {event.block.content[-50:]}")
            case EventType.BLOCK_CLOSED:
                print(f"Finished: {event.block.block_type}")
                current_block = None
```

## Multiple Syntax Support

Combine multiple syntaxes for flexible parsing:

```python
processor = StreamBlockProcessor(
    syntaxes=[
        MarkdownFrontmatterSyntax(),  # YAML frontmatter
        FencedCodeSyntax(),           # Code blocks
        DelimiterFrontmatterSyntax(), # Custom delimiters
    ]
)
```

## Filtering Events

Process only specific event types:

```python
async def get_text_only(stream):
    processor = StreamBlockProcessor(
        emit_text_delta=True,
        emit_block_events=False,  # Skip block events
    )

    text = ""
    async for event in processor.process_stream(stream):
        if event.type == EventType.TEXT_DELTA:
            text += event.data

    return text
```

## Block Type Routing

Route blocks to different handlers:

```python
handlers = {
    "message": handle_message,
    "tool_call": handle_tool_call,
    "code": handle_code,
}

async for event in processor.process_stream(stream):
    if event.type == EventType.BLOCK_CLOSED:
        block = event.block
        handler = handlers.get(block.block_type)
        if handler:
            await handler(block)
```

## Error Recovery

Continue processing after errors:

```python
async def process_with_recovery(stream):
    processor = StreamBlockProcessor(syntaxes=[MarkdownFrontmatterSyntax()])

    async for event in processor.process_stream(stream):
        try:
            if event.type == EventType.BLOCK_CLOSED:
                process_block(event.block)
        except Exception as e:
            logger.error(f"Error processing block: {e}")
            continue  # Continue with next event
```

## Chaining Processors

Use multiple processors for different stages:

```python
# First pass: extract raw blocks
raw_processor = StreamBlockProcessor(syntaxes=[MarkdownFrontmatterSyntax()])

# Second pass: validate and transform
async def process_pipeline(stream):
    async for event in raw_processor.process_stream(stream):
        if event.type == EventType.BLOCK_CLOSED:
            validated = validate_block(event.block)
            if validated:
                yield transform_block(validated)
```
