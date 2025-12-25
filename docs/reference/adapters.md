# Adapters

Stream adapters for converting provider-specific formats.

## Overview

Adapters convert provider-specific stream formats into text chunks that StreamBlocks can process. Each adapter implements a callable interface that transforms the input stream.

## Provider Adapters

### GeminiAdapter

Adapter for Google Gemini streams.

```python
from hother.streamblocks.adapters import GeminiAdapter

adapter = GeminiAdapter()
async for event in processor.process_stream(adapter(gemini_response)):
    ...
```

### OpenAIAdapter

Adapter for OpenAI streams.

```python
from hother.streamblocks.adapters import OpenAIAdapter

adapter = OpenAIAdapter()
async for event in processor.process_stream(adapter(openai_response)):
    ...
```

### AnthropicAdapter

Adapter for Anthropic streams.

```python
from hother.streamblocks.adapters import AnthropicAdapter

adapter = AnthropicAdapter()
async for event in processor.process_stream(adapter(anthropic_stream)):
    ...
```

## Auto-Detection

StreamBlocks can automatically detect the appropriate adapter:

```python
from hother.streamblocks.adapters import auto_detect_adapter

adapter = auto_detect_adapter(response)
if adapter:
    async for event in processor.process_stream(adapter(response)):
        ...
```

## Creating Custom Adapters

Create custom adapters by implementing a callable that yields text chunks:

```python
class MyProviderAdapter:
    def __call__(self, stream):
        for chunk in stream:
            # Extract text from provider-specific format
            yield chunk.text
```

## API Reference

::: hother.streamblocks.adapters
    options:
      show_root_heading: true
      show_source: false
      members_order: source
