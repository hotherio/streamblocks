# Troubleshooting

Common issues and solutions for StreamBlocks.

## Blocks Not Detected

**Problem**: Blocks are not being detected from the stream.

**Solutions**:

1. **Check syntax configuration**: Ensure you've registered the correct syntax in the registry:
   ```python
   from hother.streamblocks import Registry, StreamBlockProcessor, MarkdownFrontmatterSyntax

   syntax = MarkdownFrontmatterSyntax()
   registry = Registry(syntax=syntax)
   # Register your block types...
   processor = StreamBlockProcessor(registry)
   ```

2. **Verify block format**: Ensure your blocks match the expected format:
   ```markdown
   ---
   type: message
   ---
   Content here
   ```

3. **Enable debug logging**:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

## Events Not Emitted

**Problem**: Expected events are not being emitted.

**Solutions**:

1. **Check event flags**: Use ProcessorConfig to control which events are emitted:
   ```python
   from hother.streamblocks import StreamBlockProcessor
   from hother.streamblocks.core.processor import ProcessorConfig

   config = ProcessorConfig(
       emit_text_deltas=True,       # Enable text delta events
       emit_section_end_events=True, # Enable section end events
   )
   processor = StreamBlockProcessor(registry, config=config)
   ```

2. **Verify stream is being consumed**:
   ```python
   async for event in processor.process_stream(stream):
       print(event)  # Ensure iteration happens
   ```

## Adapter Issues

**Problem**: Stream adapter not working correctly.

**Solutions**:

1. **Use correct adapter**:
   ```python
   # For Gemini
   from hother.streamblocks.adapters import GeminiAdapter

   # For OpenAI
   from hother.streamblocks.adapters import OpenAIAdapter
   ```

2. **Try auto-detection**:
   ```python
   from hother.streamblocks.adapters import auto_detect_adapter

   adapter = auto_detect_adapter(stream)
   ```

## Import Errors

**Problem**: Cannot import StreamBlocks modules.

**Solutions**:

1. **Check installation**:
   ```bash
   pip show streamblocks
   ```

2. **Install with extras**:
   ```bash
   pip install streamblocks[gemini,openai]
   ```

## Memory Issues

**Problem**: High memory usage with large streams.

**Solutions**:

1. **Process events immediately**:
   ```python
   async for event in processor.process_stream(stream):
       handle_event(event)  # Don't accumulate
   ```

2. **Set block size limits**: Use ProcessorConfig to limit block sizes:
   ```python
   from hother.streamblocks.core.processor import ProcessorConfig

   config = ProcessorConfig(max_block_size=100_000)
   processor = StreamBlockProcessor(registry, config=config)
   ```

## Getting Help

If you're still having issues:

1. Check the [examples](examples/index.md) for working code
2. Review the [API reference](reference/index.md)
3. Open an issue on [GitHub](https://github.com/hotherio/streamblocks/issues)
