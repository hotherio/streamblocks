# StreamBlocks Adapter Examples

This directory contains comprehensive examples demonstrating the StreamBlocks adapter system for handling diverse streaming formats from AI providers.

## Table of Contents
- [What are Adapters?](#what-are-adapters)
- [Quick Start](#quick-start)
- [Example Index](#example-index)
- [Running Examples](#running-examples)
- [Choosing the Right Adapter](#choosing-the-right-adapter)
- [Configuration Options](#configuration-options)

## What are Adapters?

StreamBlocks adapters solve a critical problem: **AI providers stream data in different formats**.

- **Google Gemini**: Chunks with `.text` attribute
- **OpenAI**: `ChatCompletionChunk` with nested `choices[0].delta.content`
- **Anthropic**: Event-based streams (`ContentBlockDelta`, `MessageStop`, etc.)
- **Plain text**: Simple strings

Adapters provide a unified interface to extract text from any chunk format while preserving access to provider-specific metadata and original events.

### Key Features

1. **Auto-Detection**: Automatically detects chunk type from first chunk
2. **Mixed Event Streams**: Yields both original chunks AND StreamBlocks events
3. **Real-Time Text Deltas**: Stream text character-by-character before line completion
4. **Metadata Access**: Preserve provider metadata (token counts, finish reasons, etc.)
5. **Configurable**: Control event emission for performance optimization

## Prerequisites

### Optional Dependencies

StreamBlocks supports multiple AI providers through optional dependencies:

```bash
# Install with specific provider support
pip install streamblocks[gemini]      # For Google Gemini
pip install streamblocks[openai]      # For OpenAI
pip install streamblocks[anthropic]   # For Anthropic Claude

# Install all providers at once
pip install streamblocks[all-providers]

# Install multiple specific providers
pip install streamblocks[gemini,openai]
```

### API Keys

Provider-specific examples require API keys:

- **Gemini** (Example 02): Set `GOOGLE_API_KEY` or `GEMINI_API_KEY`
  - Get key: https://aistudio.google.com/apikey
  - Model used: `gemini-2.5-flash`

- **OpenAI** (Example 03): Set `OPENAI_API_KEY`
  - Get key: https://platform.openai.com/api-keys
  - Model used: `gpt-5-nano-2025-08-07`

- **Anthropic** (Example 04): Set `ANTHROPIC_API_KEY`
  - Get key: https://console.anthropic.com/settings/keys
  - Model used: `claude-3.5-haiku`

**Note:** Examples 01, 05-12 work without any API keys (use plain text or mocks). Example 13 requires a Gemini API key.

## Quick Start

```python
from hother.streamblocks import StreamBlockProcessor, Registry

# Plain text (no adapter needed)
processor = StreamBlockProcessor(registry)
async for event in processor.process_stream(text_stream()):
    # Handle events
    pass

# Auto-detect provider format
async for event in processor.process_stream(gemini_stream()):
    # Automatically detects and uses GeminiAdapter
    pass

# Explicit adapter
from hother.streamblocks import OpenAIAdapter
async for event in processor.process_stream(openai_stream(), adapter=OpenAIAdapter()):
    # Use specific adapter
    pass
```

## Example Index

| # | Example | Purpose | Key Concepts | Requires |
|---|---------|---------|--------------|----------|
| 01 | [Identity Adapter](#01-identity-adapter) | Plain text streaming | Default behavior, no adapter needed | None |
| 02 | [Gemini Auto-Detect](#02-gemini-auto-detect) | Gemini stream handling | Auto-detection, metadata access | Gemini API key |
| 03 | [OpenAI Explicit](#03-openai-explicit) | OpenAI stream handling | Explicit adapter, finish_reason | OpenAI API key |
| 04 | [Anthropic Adapter](#04-anthropic-adapter) | Anthropic events | Event-based streaming, stop reasons | Anthropic API key |
| 05 | [Mixed Event Stream](#05-mixed-event-stream) | Type checking | isinstance(), counting events | None |
| 06 | [Text Delta Streaming](#06-text-delta-streaming) | Real-time text | Typewriter effect, char-by-char | None |
| 07 | [Block Opened Event](#07-block-opened-event) | Early detection | React before content arrives | None |
| 08 | [Configuration Flags](#08-configuration-flags) | Performance tuning | All config options compared | None |
| 09 | [Custom Adapter](#09-custom-adapter) | Proprietary formats | Custom adapter creation | None |
| 10 | [Callable Adapter](#10-callable-adapter) | Quick prototyping | Lambda-based extraction | None |
| 11 | [Attribute Adapter](#11-attribute-adapter) | Generic objects | Any text-like attribute | None |
| 12 | [Disable Original Events](#12-disable-original-events) | Performance | Lightweight mode comparison | None |
| 13 | [Manual Chunk Processing](#13-manual-chunk-processing) | Fine-grained control | process_chunk(), finalize(), batch processing | Gemini API key |

### 01: Identity Adapter
**File**: `01_identity_adapter_plain_text.py`

Basic plain text streaming - the default behavior. Shows all event types without needing an adapter.

**When to use**: Working with plain text strings, simple demos, learning basics.

```bash
uv run examples/adapters/01_identity_adapter_plain_text.py
```

### 02: Gemini Auto-Detect
**File**: `02_gemini_auto_detect.py`

Demonstrates automatic detection of Gemini chunks and access to provider metadata.

**When to use**: Google Gemini integration, want auto-detection, need usage metadata.

```bash
uv run examples/adapters/02_gemini_auto_detect.py
```

### 03: OpenAI Explicit
**File**: `03_openai_explicit_adapter.py`

Shows explicit OpenAI adapter usage and finish reason access.

**When to use**: OpenAI integration, want explicit control, need finish_reason.

```bash
uv run examples/adapters/03_openai_explicit_adapter.py
```

### 04: Anthropic Adapter
**File**: `04_anthropic_adapter.py`

Handles Anthropic's event-based streaming format with different event types.

**When to use**: Anthropic integration, event-based streams, stop reason handling.

```bash
uv run examples/adapters/04_anthropic_adapter.py
```

### 05: Mixed Event Stream
**File**: `05_mixed_event_stream.py`

Demonstrates type checking in mixed streams with both original chunks and StreamBlocks events.

**When to use**: Need access to both original and processed events, event counting, debugging.

```bash
uv run examples/adapters/05_mixed_event_stream.py
```

### 06: Text Delta Streaming
**File**: `06_text_delta_streaming.py`

Real-time character-by-character streaming with typewriter effects.

**When to use**: Live UI updates, progress indicators, typewriter effects, chat interfaces.

```bash
uv run examples/adapters/06_text_delta_streaming.py
```

### 07: Block Opened Event
**File**: `07_block_opened_event.py`

React to BlockOpenedEvent before block content arrives.

**When to use**: Prepare UI early, show loading states, progressive disclosure.

```bash
uv run examples/adapters/07_block_opened_event.py
```

### 08: Configuration Flags
**File**: `08_configuration_flags.py`

Comprehensive comparison of all processor configuration options.

**When to use**: Performance tuning, understanding configuration impact, choosing optimal settings.

```bash
uv run examples/adapters/08_configuration_flags.py
```

### 09: Custom Adapter
**File**: `09_custom_adapter.py`

Create and register custom adapter for proprietary streaming formats.

**When to use**: Custom/proprietary API formats, specific extraction needs, advanced use cases.

```bash
uv run examples/adapters/09_custom_adapter.py
```

### 10: Callable Adapter
**File**: `10_callable_adapter.py`

Quick lambda-based adapter without creating a full class.

**When to use**: Rapid prototyping, simple extraction needs, one-off integrations.

```bash
uv run examples/adapters/10_callable_adapter.py
```

### 11: Attribute Adapter
**File**: `11_attribute_adapter_generic.py`

Generic adapter for any object with a text-like attribute.

**When to use**: Generic chunk objects, unknown formats, flexible integration.

```bash
uv run examples/adapters/11_attribute_adapter_generic.py
```

### 12: Disable Original Events
**File**: `12_disable_original_events.py`

Performance comparison between normal and lightweight mode.

**When to use**: Performance optimization, batch processing, don't need original chunks.

```bash
uv run examples/adapters/12_disable_original_events.py
```

### 13: Manual Chunk Processing
**File**: `13_manual_chunk_processing.py`

Demonstrates manual chunk-by-chunk processing using `process_chunk()` and `finalize()` methods, showing three different patterns:
1. **Basic manual processing**: Process each chunk individually and handle events
2. **Selective processing**: Apply custom logic to filter which chunks to process
3. **Batch processing**: Buffer chunks and process in batches

**When to use**:
- Need fine-grained control over chunk processing
- Custom buffering or batching strategies
- Selective processing based on chunk content
- Integration with existing async pipelines
- Processing chunks from multiple sources
- Synchronous processing API required

**Key methods:**
- `process_chunk(chunk)`: Process a single chunk, returns list of events
- `finalize()`: Flush incomplete blocks after processing all chunks

**Important**: Always call `finalize()` after processing all chunks to get rejection events for incomplete blocks.

```bash
uv run examples/adapters/13_manual_chunk_processing.py
```

## Running Examples

All examples are self-contained and can be run directly:

```bash
# Run a specific example
uv run examples/adapters/01_identity_adapter_plain_text.py

# Run all examples
for example in examples/adapters/*.py; do
    echo "Running $example..."
    uv run "$example"
    echo ""
done
```

## Choosing the Right Adapter

### By Provider

| Provider | Adapter | Auto-Detect? | Example |
|----------|---------|--------------|---------|
| Plain text | `IdentityAdapter` (default) | ✅ Yes | 01 |
| Google Gemini | `GeminiAdapter` | ✅ Yes | 02 |
| OpenAI | `OpenAIAdapter` | ✅ Yes | 03 |
| Anthropic | `AnthropicAdapter` | ✅ Yes | 04 |
| Generic object | `AttributeAdapter` | ❌ No | 11 |
| Lambda/Function | `CallableAdapter` | ❌ No | 10 |
| Custom format | Custom class | ✅ Optional | 09 |

### By Use Case

| Use Case | Recommended Approach | Examples |
|----------|---------------------|----------|
| Quick prototyping | `CallableAdapter` | 10 |
| Production AI integration | Auto-detection + provider adapters | 02, 03, 04 |
| Real-time UI updates | Enable `emit_text_deltas=True` | 06 |
| Performance-critical | Disable original events | 12 |
| Custom API | Create custom adapter | 09 |
| Generic objects | `AttributeAdapter` | 11 |
| Debugging/Logging | Enable all events, mixed streams | 05, 08 |
| Fine-grained control | Manual chunk processing | 13 |
| Custom buffering/batching | `process_chunk()` + custom logic | 13 |

## Configuration Options

### Processor Configuration

```python
processor = StreamBlockProcessor(
    registry,
    emit_original_events=True,   # Pass through original chunks
    emit_text_deltas=True,       # Real-time text streaming
    auto_detect_adapter=True,    # Auto-detect from first chunk
)
```

### Configuration Matrix

| Configuration | Original Chunks | Text Deltas | Blocks | Use Case |
|--------------|----------------|-------------|--------|----------|
| Default | ✅ | ✅ | ✅ | Full transparency + real-time |
| Lightweight | ❌ | ✅ | ✅ | Performance, no original data |
| Line-based | ✅ | ❌ | ✅ | Batch processing |
| Minimal | ❌ | ❌ | ✅ | Maximum performance |

See **Example 08** for detailed comparison.

## Event Types

When processing streams with adapters, you'll encounter these event types:

### Original Events
- **Provider chunks**: Original objects from AI provider streams
- Preserved when `emit_original_events=True`
- Contains provider-specific metadata

### StreamBlocks Events

1. **`RawTextEvent`**: Complete text outside blocks
2. **`TextDeltaEvent`**: Real-time text streaming (when `emit_text_deltas=True`)
   - `delta`: Text fragment
   - `inside_block`: Whether inside a block
   - `block_section`: Current block section (preamble, content, etc.)
3. **`BlockOpenedEvent`**: Block detected (before content processed)
   - `syntax`: Syntax type name
   - `start_line`: Line number
   - `inline_metadata`: Metadata from opening delimiter
4. **`BlockExtractedEvent`**: Complete block extracted
   - `block`: Full Block object with metadata and content
5. **`BlockRejectedEvent`**: Block failed validation
   - `error`: Reason for rejection

### Type Checking

```python
from hother.streamblocks import (
    TextDeltaEvent,
    BlockExtractedEvent,
    RawTextEvent,
)

async for event in processor.process_stream(stream):
    # Original chunks
    if isinstance(event, MyChunkType):
        print(f"Original: {event}")

    # Text streaming
    elif isinstance(event, TextDeltaEvent):
        print(event.delta, end="", flush=True)

    # Blocks
    elif isinstance(event, BlockExtractedEvent):
        print(f"Block: {event.block.metadata.id}")
```

## Performance Considerations

### Event Overhead

| Configuration | Events/Chunk | Overhead | Recommendation |
|--------------|-------------|----------|----------------|
| Full (default) | 2-3 | ~2-5% | Most use cases |
| No originals | 1-2 | ~1-2% | Batch processing |
| No deltas | 1-2 | ~1-2% | Non-interactive |
| Minimal | 0-1 | ~0% | Performance-critical |

### When to Optimize

✅ **Disable original events** when:
- Don't need provider metadata
- Processing large volumes
- Memory constrained
- Only care about extracted blocks

✅ **Disable text deltas** when:
- No real-time UI updates needed
- Batch/offline processing
- Only need complete lines
- Maximum performance required

See **Example 12** for performance comparison.

## Advanced Topics

### Custom Adapter Creation

See **Example 09** for full details. Basic structure:

```python
from hother.streamblocks import StreamAdapter

class MyAdapter(StreamAdapter):
    def extract_text(self, chunk: MyChunk) -> str | None:
        return chunk.text_field

    def is_complete(self, chunk: MyChunk) -> bool:
        return chunk.done

    def get_metadata(self, chunk: MyChunk) -> dict | None:
        return {"my_metadata": chunk.meta}
```

### Adapter Registration

```python
from hother.streamblocks import AdapterDetector

# Register for auto-detection
AdapterDetector.register_adapter(
    module_prefix="mycompany.api",
    adapter_class=MyAdapter,
)
```

## Common Patterns

### Pattern: Typewriter Effect
```python
async for event in processor.process_stream(stream):
    if isinstance(event, TextDeltaEvent):
        print(event.delta, end="", flush=True)
```

### Pattern: Prepare UI Early
```python
async for event in processor.process_stream(stream):
    if isinstance(event, BlockOpenedEvent):
        ui.prepare_widget(event.syntax)
```

### Pattern: Count Events
```python
counts = {"original": 0, "deltas": 0, "blocks": 0}
async for event in processor.process_stream(stream):
    if isinstance(event, MyChunk):
        counts["original"] += 1
    elif isinstance(event, TextDeltaEvent):
        counts["deltas"] += 1
    elif isinstance(event, BlockExtractedEvent):
        counts["blocks"] += 1
```

### Pattern: Access Provider Metadata
```python
async for event in processor.process_stream(stream):
    if isinstance(event, GeminiChunk):
        if hasattr(event, "usage_metadata"):
            print(f"Tokens: {event.usage_metadata.total_token_count}")
```

## Troubleshooting

### ImportError: No module named 'google.genai'

Install the Gemini provider SDK:
```bash
pip install streamblocks[gemini]
# Or directly:
pip install google-genai
```

### ImportError: No module named 'openai'

Install the OpenAI provider SDK:
```bash
pip install streamblocks[openai]
# Or directly:
pip install openai
```

### ImportError: No module named 'anthropic'

Install the Anthropic provider SDK:
```bash
pip install streamblocks[anthropic]
# Or directly:
pip install anthropic
```

### Missing API Key Errors

Ensure environment variables are set:
```bash
export GOOGLE_API_KEY="your-key-here"
export OPENAI_API_KEY="your-key-here"
export ANTHROPIC_API_KEY="your-key-here"
```

### Auto-Detection Not Working

1. Check chunk's `__module__` attribute
2. Try explicit adapter: `processor.process_stream(stream, adapter=MyAdapter())`
3. Use `AttributeAdapter` for generic objects
4. See **Example 11** for generic handling

### No Original Events

- Check `emit_original_events=True` in processor config
- Verify not using `IdentityAdapter` (it doesn't emit originals to avoid duplication)
- See **Example 05** for mixed event streams

### No Text Deltas

- Check `emit_text_deltas=True` in processor config
- Verify adapter is extracting text correctly
- See **Example 06** for real-time streaming

## Further Reading

- [StreamBlocks Documentation](../../README.md)
- [Adapter Protocol](../../src/hother/streamblocks/adapters/base.py)
- [Built-in Adapters](../../src/hother/streamblocks/adapters/providers.py)
- [Auto-Detection System](../../src/hother/streamblocks/adapters/detection.py)

## Summary

This directory provides 13 comprehensive examples covering:

- ✅ All built-in adapters (Identity, Gemini, OpenAI, Anthropic, Callable, Attribute)
- ✅ Auto-detection and explicit adapter usage
- ✅ Mixed event streams with type checking
- ✅ Real-time text streaming
- ✅ Configuration options and performance tuning
- ✅ Custom adapter creation and registration
- ✅ Manual chunk processing with fine-grained control
- ✅ Common patterns and use cases

Start with **Example 01** for basics, then explore examples relevant to your use case. For fine-grained control over processing, see **Example 13** for manual chunk processing patterns.
