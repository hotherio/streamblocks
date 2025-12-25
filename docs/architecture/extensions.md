# Extension System

Streamblocks uses a modular extension architecture to support multiple LLM providers and output protocols. This design keeps the core library lightweight while enabling rich integrations.

## Overview

```mermaid
flowchart TB
    subgraph Core["Core Package: streamblocks"]
        Processor[StreamBlockProcessor]
        Registry[BlockRegistry]
        Syntax[Syntax]
        Events[Events]
        BaseAdapter[Base Adapters]
    end

    subgraph Extras["Optional Extras"]
        GeminiExt["streamblocks[gemini]"]
        OpenAIExt["streamblocks[openai]"]
        AnthropicExt["streamblocks[anthropic]"]
        AGUIExt["streamblocks[agui]"]
    end

    subgraph ExtModules["Extension Modules"]
        GeminiMod[streamblocks.ext.gemini]
        OpenAIMod[streamblocks.ext.openai]
        AnthropicMod[streamblocks.ext.anthropic]
        AGUIMod[streamblocks.ext.agui]
    end

    Core --> GeminiExt
    Core --> OpenAIExt
    Core --> AnthropicExt
    Core --> AGUIExt

    GeminiExt --> GeminiMod
    OpenAIExt --> OpenAIMod
    AnthropicExt --> AnthropicMod
    AGUIExt --> AGUIMod
```

## Extension Structure

Each extension follows a consistent structure:

```
streamblocks/
├── ext/
│   ├── gemini/
│   │   ├── __init__.py      # Public exports
│   │   ├── adapter.py       # Input adapter
│   │   └── types.py         # Provider types
│   ├── openai/
│   │   ├── __init__.py
│   │   ├── adapter.py
│   │   └── types.py
│   ├── anthropic/
│   │   ├── __init__.py
│   │   ├── adapter.py
│   │   └── types.py
│   └── agui/
│       ├── __init__.py
│       ├── input_adapter.py  # Input adapter
│       ├── output_adapter.py # Output adapter
│       └── types.py
```

## Adapter Protocol

Extensions implement the adapter protocol to integrate with the core processor:

```mermaid
classDiagram
    class InputAdapter {
        <<protocol>>
        +categorize(event: Any) EventCategory
        +extract_text(event: Any) str
    }

    class OutputAdapter {
        <<protocol>>
        +to_protocol_event(event: StreamEvent) Any
        +passthrough(event: Any) Any
    }

    class GeminiInputAdapter {
        +categorize(event) EventCategory
        +extract_text(event) str
    }

    class OpenAIInputAdapter {
        +categorize(event) EventCategory
        +extract_text(event) str
    }

    class AnthropicInputAdapter {
        +categorize(event) EventCategory
        +extract_text(event) str
    }

    class AGUIInputAdapter {
        +categorize(event) EventCategory
        +extract_text(event) str
    }

    class AGUIOutputAdapter {
        +to_protocol_event(event) AGUIEvent
        +passthrough(event) AGUIEvent
    }

    InputAdapter <|.. GeminiInputAdapter
    InputAdapter <|.. OpenAIInputAdapter
    InputAdapter <|.. AnthropicInputAdapter
    InputAdapter <|.. AGUIInputAdapter
    OutputAdapter <|.. AGUIOutputAdapter
```

### Event Categories

Input adapters categorize incoming events:

```python
class EventCategory(Enum):
    """Categories for incoming events."""

    TEXT_CONTENT = "text_content"      # Contains extractable text
    PASSTHROUGH = "passthrough"        # Pass through unchanged
    SKIP = "skip"                      # Ignore this event
    STREAM_START = "stream_start"      # Stream is starting
    STREAM_END = "stream_end"          # Stream is ending
```

### Categorization Flow

```mermaid
sequenceDiagram
    participant Provider as LLM Provider
    participant Adapter as Input Adapter
    participant Processor as StreamBlockProcessor
    participant Output as Output

    Provider->>Adapter: Raw event
    Adapter->>Adapter: categorize(event)

    alt TEXT_CONTENT
        Adapter->>Adapter: extract_text(event)
        Adapter->>Processor: text chunk
        Processor->>Output: StreamEvent
    else PASSTHROUGH
        Adapter->>Output: Original event
    else SKIP
        Note over Adapter: Event discarded
    else STREAM_START
        Adapter->>Processor: Signal start
        Processor->>Output: STREAM_START event
    else STREAM_END
        Adapter->>Processor: Signal end
        Processor->>Output: STREAM_END event
    end
```

## Provider Extensions

### Gemini Extension

Handles Google Gemini API responses:

```python
from streamblocks.ext.gemini import GeminiInputAdapter

# Automatic adapter selection
processor = StreamBlockProcessor(
    registry=registry,
    syntax=syntax,
    input_adapter="auto",  # Detects Gemini events
)

# Explicit adapter
adapter = GeminiInputAdapter()
processor = StreamBlockProcessor(
    registry=registry,
    syntax=syntax,
    input_adapter=adapter,
)
```

Event handling:

| Gemini Event | Category | Action |
|--------------|----------|--------|
| `GenerateContentResponse` | TEXT_CONTENT | Extract text from candidates |
| Stream start | STREAM_START | Initialize processing |
| Stream end | STREAM_END | Finalize processing |

### OpenAI Extension

Handles OpenAI API streaming responses:

```python
from streamblocks.ext.openai import OpenAIInputAdapter

adapter = OpenAIInputAdapter()
processor = StreamBlockProcessor(
    registry=registry,
    syntax=syntax,
    input_adapter=adapter,
)
```

Event handling:

| OpenAI Event | Category | Action |
|--------------|----------|--------|
| `ChatCompletionChunk` | TEXT_CONTENT | Extract delta content |
| `[DONE]` | STREAM_END | Finalize processing |

### Anthropic Extension

Handles Anthropic Claude streaming events:

```python
from streamblocks.ext.anthropic import AnthropicInputAdapter

adapter = AnthropicInputAdapter()
processor = StreamBlockProcessor(
    registry=registry,
    syntax=syntax,
    input_adapter=adapter,
)
```

Event handling:

| Anthropic Event | Category | Action |
|-----------------|----------|--------|
| `ContentBlockDelta` | TEXT_CONTENT | Extract text delta |
| `MessageStart` | STREAM_START | Initialize |
| `MessageStop` | STREAM_END | Finalize |
| `ContentBlockStart/Stop` | SKIP | Internal events |

### AG-UI Extension

Bidirectional adapter for the AG-UI protocol:

```python
from streamblocks.ext.agui import AGUIInputAdapter, AGUIOutputAdapter

input_adapter = AGUIInputAdapter()
output_adapter = AGUIOutputAdapter()

processor = StreamBlockProcessor(
    registry=registry,
    syntax=syntax,
    input_adapter=input_adapter,
    output_adapter=output_adapter,
)
```

```mermaid
flowchart LR
    subgraph AGUI["AG-UI Protocol"]
        AGUIIn[Incoming Events]
        AGUIOut[Outgoing Events]
    end

    subgraph Streamblocks["Streamblocks"]
        Input[AGUIInputAdapter]
        Processor[Processor]
        Output[AGUIOutputAdapter]
    end

    AGUIIn --> Input
    Input --> Processor
    Processor --> Output
    Output --> AGUIOut
```

## Creating Custom Extensions

### Step 1: Define Types

```python
# my_extension/types.py
from dataclasses import dataclass
from typing import Any

@dataclass
class MyProviderEvent:
    """Event from my provider."""
    type: str
    content: str | None
    metadata: dict[str, Any]
```

### Step 2: Implement Input Adapter

```python
# my_extension/adapter.py
from streamblocks.adapters import EventCategory

class MyProviderInputAdapter:
    """Input adapter for my provider."""

    def categorize(self, event: Any) -> EventCategory:
        """Categorize an incoming event."""
        if isinstance(event, MyProviderEvent):
            if event.type == "content":
                return EventCategory.TEXT_CONTENT
            elif event.type == "start":
                return EventCategory.STREAM_START
            elif event.type == "end":
                return EventCategory.STREAM_END
        return EventCategory.SKIP

    def extract_text(self, event: Any) -> str:
        """Extract text from a TEXT_CONTENT event."""
        if isinstance(event, MyProviderEvent):
            return event.content or ""
        return ""
```

### Step 3: Register as Extra (Optional)

In `pyproject.toml`:

```toml
[project.optional-dependencies]
my-provider = ["my-provider-sdk>=1.0"]

[project.entry-points."streamblocks.adapters"]
my-provider = "my_extension:MyProviderInputAdapter"
```

## Extension Loading

Extensions are loaded on-demand:

```mermaid
flowchart TB
    subgraph Import["Import Stage"]
        Core[import streamblocks]
        CheckExtra{Extra installed?}
        LoadExt[Load extension]
        Skip[Skip extension]
    end

    subgraph Use["Usage Stage"]
        CreateProcessor[Create processor]
        AutoDetect{Auto-detect?}
        TryAdapters[Try registered adapters]
        UseAdapter[Use matching adapter]
        UseIdentity[Use identity adapter]
    end

    Core --> CheckExtra
    CheckExtra -->|Yes| LoadExt
    CheckExtra -->|No| Skip

    CreateProcessor --> AutoDetect
    AutoDetect -->|Yes| TryAdapters
    AutoDetect -->|No| UseAdapter
    TryAdapters -->|Match| UseAdapter
    TryAdapters -->|No match| UseIdentity
```

## Best Practices

!!! tip "Keep Extensions Focused"
    Each extension should handle one provider. Don't combine multiple providers in a single extension.

!!! tip "Use Protocol, Not Inheritance"
    Implement the adapter protocol rather than inheriting from base classes. This keeps extensions decoupled.

!!! tip "Handle Unknown Events Gracefully"
    Return `EventCategory.SKIP` for unrecognized events rather than raising errors.

!!! tip "Document Event Mappings"
    Clearly document how provider events map to Streamblocks events.

## Next Steps

- [State Machine](state-machine.md) - Block detection internals
- [Adapter Protocol](adapters.md) - Detailed adapter documentation
- [API Reference](../reference/extensions.md) - Extension API details
