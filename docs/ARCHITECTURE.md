# StreamBlocks Architecture

This document describes the architecture of StreamBlocks, a Python library for real-time extraction and processing of structured blocks from text streams.

## Overview

### Design Philosophy

StreamBlocks is built around these core principles:

1. **Real-time Processing**: Process streams as they arrive, without waiting for complete input
2. **Event-Driven**: Emit fine-grained events for each processing stage
3. **Single Syntax per Processor**: Each processor works with exactly one syntax for simplicity
4. **Extensible**: Support custom syntaxes, validators, and adapters
5. **Type-Safe**: Full typing with Pydantic models and generics

### Core Concepts

- **Block**: A structured region within a text stream (e.g., code fence, YAML frontmatter)
- **Syntax**: Rules for detecting and parsing blocks (e.g., delimiter-based, markdown-based)
- **Registry**: Maps block types to block classes and validators
- **Event**: Notification of processing progress (start, delta, end, error)
- **Adapter**: Extracts text from provider-specific stream formats (Gemini, OpenAI, etc.)

---

## Component Architecture

### StreamBlockProcessor

The main orchestrator that processes text streams and emits events.

```
StreamBlockProcessor
├── registry: Registry          # Block type mappings
├── syntax: BaseSyntax          # Syntax for detection/parsing
├── _candidates: list           # Active block candidates
├── _accumulated_text: list     # Text buffer for line assembly
├── _line_counter: int          # Current line number
└── _buffer: deque              # Recent lines buffer
```

**Key Methods:**
- `process_stream(stream, adapter)` - Async stream processing with auto adapter detection
- `process_chunk(chunk, adapter)` - Sync chunk processing for fine-grained control
- `finalize()` - Flush incomplete blocks at stream end

### Registry

Maps block types to block classes and manages validators.

```python
registry = Registry(syntax=DelimiterPreambleSyntax())
registry.register("files_operations", FileOperations, validators=[my_validator])
registry.register("patch", Patch)
```

**Responsibilities:**
- Hold exactly one syntax instance
- Map block type strings to Block classes
- Manage per-type validators
- Validate extracted blocks

### BlockCandidate

Tracks a potential block being accumulated.

```python
class BlockCandidate:
    syntax: BaseSyntax           # Syntax handler
    start_line: int              # Starting line number
    lines: list[str]             # Accumulated lines
    state: BlockState            # Current state
    current_section: str | None  # "header", "metadata", or "content"
```

**State Transitions:**
```
HEADER_DETECTED → ACCUMULATING_METADATA → ACCUMULATING_CONTENT → CLOSING_DETECTED
                                      ↓                      ↓
                                 REJECTED              COMPLETED
```

### BaseSyntax

Abstract protocol for syntax implementations.

```python
class BaseSyntax(ABC):
    @abstractmethod
    def detect_line(line, candidate) -> DetectionResult

    @abstractmethod
    def should_accumulate_metadata(candidate) -> bool

    @abstractmethod
    def extract_block_type(candidate) -> str | None

    @abstractmethod
    def parse_block(candidate, block_class) -> ParseResult

    def validate_block(block) -> bool  # Default: True
```

**Built-in Syntaxes:**
- `DelimiterPreambleSyntax` - `!!id:type` format with preamble metadata
- `DelimiterFrontmatterSyntax` - Delimiter with YAML frontmatter
- `MarkdownFrontmatterSyntax` - Markdown code fence with frontmatter

### Event Types

Hierarchical event system for fine-grained processing feedback.

```
BaseEvent
├── Lifecycle Events
│   ├── StreamStartedEvent
│   ├── StreamFinishedEvent
│   └── StreamErrorEvent
├── Text Events
│   ├── TextContentEvent      # Complete line outside blocks
│   └── TextDeltaEvent        # Real-time chunk (before line completion)
└── Block Events
    ├── BlockStartEvent       # Opening detected
    ├── BlockHeaderDeltaEvent # Header section content
    ├── BlockMetadataDeltaEvent # Metadata section content
    ├── BlockContentDeltaEvent  # Content section content
    ├── BlockEndEvent         # Successfully extracted
    └── BlockErrorEvent       # Failed validation/unclosed/size exceeded
```

---

## Processing Pipeline

### Component Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                    StreamBlockProcessor                         │
│                        (Orchestrator)                           │
│                                                                 │
│   - Adapter detection & text extraction                         │
│   - TextDeltaEvent emission                                     │
│   - Coordinates LineAccumulator and BlockStateMachine           │
└───────────────────────┬─────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│ LineAccumulator│ │BlockStateMachine│ │   Registry    │
│               │ │               │ │               │
│ - Text buffer │ │ - Candidates  │ │ - Block types │
│ - Line split  │ │ - Detection   │ │ - Validators  │
│ - Truncation  │ │ - Extraction  │ │               │
└───────────────┘ └───────────────┘ └───────────────┘
```

### Data Flow

```
Raw Stream Chunk
    ↓
[StreamBlockProcessor: Adapter → Extract Text]
    ↓
TextDeltaEvent (real-time, if enabled)
    ↓
[LineAccumulator: Accumulate → Split on \n]
    ↓
Complete Lines (with line numbers)
    ↓
[BlockStateMachine: detect_line() for each line]
    ├─ No block: TextContentEvent
    ├─ Opening: BlockStartEvent → create BlockCandidate
    ├─ Inside: BlockHeaderDelta / BlockMetadataDelta / BlockContentDelta
    └─ Closing: BlockEndEvent (success) or BlockErrorEvent (failure)
```

### LineAccumulator

The `LineAccumulator` class handles text-to-line conversion:

```python
from hother.streamblocks.core.line_accumulator import LineAccumulator

acc = LineAccumulator(max_line_length=16_384, buffer_size=5)

# Add text, get complete lines with line numbers
lines = acc.add_text("Hello\nWor")  # Returns [(1, "Hello"), (2, "")]
lines = acc.add_text("ld\n")        # Returns [(3, "World"), (4, "")]

# Finalize remaining text
final = acc.finalize()  # Returns (line_num, text) or None
```

**Responsibilities:**
- Accumulate text chunks until newlines
- Split on `\n` boundaries (trailing newline creates empty line)
- Track line numbers (1-indexed)
- Truncate lines exceeding `max_line_length`
- Maintain circular buffer of recent lines
- Handle final incomplete text on `finalize()`

**Key Behavior:**
- `"Hello\n".split("\n")` returns `["Hello", ""]` - trailing empty is included
- Line numbers increment for each line including empty ones
- Buffer maintains last `buffer_size` lines for context

### BlockStateMachine

The `BlockStateMachine` class manages block detection, accumulation, and extraction:

```python
from hother.streamblocks.core.block_state_machine import BlockStateMachine

machine = BlockStateMachine(syntax, registry, max_block_size=1_048_576)

# Process lines
for line_num, line in lines:
    events = machine.process_line(line, line_num)
    for event in events:
        handle(event)

# Flush remaining candidates at stream end
final_events = machine.flush(current_line_number=last_line)
```

**Responsibilities:**
- Detect block openings and closings via syntax
- Manage active `BlockCandidate` instances
- Emit events: `BlockStartEvent`, section deltas, `BlockEndEvent`, `BlockErrorEvent`
- Enforce block size limits
- Extract and validate complete blocks
- Generate `TextContentEvent` for non-block lines

**State Transitions:**
```
SEARCHING → HEADER_DETECTED → ACCUMULATING_METADATA → ACCUMULATING_CONTENT → CLOSING_DETECTED
                                                  ↓                      ↓
                                             REJECTED              COMPLETED
```

**Event Generation:**
- Opening detected → `BlockStartEvent`
- Line inside block → `BlockHeaderDeltaEvent` / `BlockMetadataDeltaEvent` / `BlockContentDeltaEvent`
- Closing detected → `BlockEndEvent` (success) or `BlockErrorEvent` (failure)
- Size exceeded → `BlockErrorEvent` with `SIZE_EXCEEDED`
- Unclosed at flush → `BlockErrorEvent` with `UNCLOSED_BLOCK`

---

## APIs

### Async Stream Processing (Recommended)

```python
async for event in processor.process_stream(stream):
    if isinstance(event, BlockEndEvent):
        print(f"Extracted: {event.block_id}")
```

**Features:**
- Automatic adapter detection (Gemini, OpenAI, Anthropic)
- Real-time event emission
- Automatic finalization at stream end

**When to use:**
- Standard AI provider integration
- Real-time streaming applications
- Simple event-driven processing

### Sync Chunk Processing

```python
for chunk in chunks:
    events = processor.process_chunk(chunk)
    for event in events:
        handle(event)

# Must call finalize at end
final_events = processor.finalize()
```

**Features:**
- Fine-grained control over processing
- Stateful between calls
- Explicit finalization required

**When to use:**
- Batch processing
- Custom buffering strategies
- Multiple sources or interleaved processing
- Integration with sync code

### Comparison

| Feature | `process_stream()` | `process_chunk()` |
|---------|-------------------|-------------------|
| Async | Yes | No |
| Auto-finalize | Yes | No (call `finalize()`) |
| Adapter detection | Automatic | Automatic on first chunk |
| Return type | AsyncGenerator | list[Event] |
| State management | Automatic | Manual |

---

## Extensibility

### Custom Syntaxes

Implement `BaseSyntax` to create custom block formats:

```python
class MySyntax(BaseSyntax):
    def detect_line(self, line, candidate):
        if line.startswith("<<<"):
            return DetectionResult(is_opening=True)
        if line.startswith(">>>"):
            return DetectionResult(is_closing=True)
        return DetectionResult()

    # ... implement other abstract methods
```

### Custom Validators

Add validation logic per block type:

```python
def validate_file_operations(block: ExtractedBlock) -> bool:
    return len(block.content.operations) > 0

registry.add_validator("files_operations", validate_file_operations)
```

### Custom Adapters

Support custom stream formats:

```python
class MyAdapter(StreamAdapter[MyChunk]):
    def extract_text(self, chunk: MyChunk) -> str | None:
        return chunk.text_content

    def is_complete(self, chunk: MyChunk) -> bool:
        return chunk.done

AdapterDetector.register_custom(MyAdapter, module_prefix="my_provider")
```

---

## Configuration

### StreamBlockProcessor Options

```python
from hother.streamblocks.core.processor import ProcessorConfig

config = ProcessorConfig(
    lines_buffer=5,             # Recent lines buffer size
    max_line_length=16_384,     # Truncate long lines
    max_block_size=1_048_576,   # Reject blocks > 1MB
    emit_original_events=True,  # Pass through provider chunks
    emit_text_deltas=True,      # Emit real-time deltas
    auto_detect_adapter=True,   # Auto-detect stream format
)
StreamBlockProcessor(registry, config=config, logger=my_logger)
```

### Size Limits

- **max_line_length**: Lines longer than this are truncated
- **max_block_size**: Blocks exceeding this size emit `BlockErrorEvent` with `SIZE_EXCEEDED`

---

## Error Handling

### Error Codes

```python
class BlockErrorCode(StrEnum):
    VALIDATION_FAILED   # Syntax or registry validation failed
    SIZE_EXCEEDED       # Block exceeded max_block_size
    UNCLOSED_BLOCK      # Stream ended without closing marker
    UNKNOWN_TYPE        # Block type not registered
    PARSE_FAILED        # Syntax couldn't parse block
    MISSING_METADATA    # Required metadata not found
    MISSING_CONTENT     # Required content not found
    SYNTAX_ERROR        # Syntax-specific error
```

### Handling Errors

```python
async for event in processor.process_stream(stream):
    if isinstance(event, BlockErrorEvent):
        print(f"Error: {event.error_code} - {event.reason}")
        print(f"Lines {event.start_line}-{event.end_line}")
```
