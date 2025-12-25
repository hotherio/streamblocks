# Core Components

Core Streamblocks components and the main processor.

## StreamBlockProcessor

The main processing engine for extracting blocks from streams.

```python
from hother.streamblocks import StreamBlockProcessor, Registry, DelimiterPreambleSyntax

processor = StreamBlockProcessor(
    registry=Registry(),
    syntaxes=[DelimiterPreambleSyntax()],
    emit_text_delta=True,
    emit_block_content_delta=True,
)

async for event in processor.process_stream(stream):
    print(event)
```

### Constructor Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `registry` | `Registry` | Required | Block type registry |
| `syntaxes` | `list[BaseSyntax]` | Required | Syntax definitions to use |
| `input_adapter` | `InputProtocolAdapter \| None` | `None` | Input stream adapter |
| `output_adapter` | `OutputProtocolAdapter \| None` | `None` | Output event adapter |
| `emit_text_delta` | `bool` | `False` | Emit TEXT_DELTA events |
| `emit_text_content` | `bool` | `True` | Emit TEXT_CONTENT events |
| `emit_block_start` | `bool` | `True` | Emit BLOCK_START events |
| `emit_block_content_delta` | `bool` | `False` | Emit delta events |
| `emit_block_metadata_end` | `bool` | `False` | Emit metadata end events |
| `emit_block_content_end` | `bool` | `False` | Emit content end events |
| `max_block_size` | `int` | `1048576` | Maximum block size in bytes |

### Methods

#### process_stream

```python
async def process_stream(
    self,
    stream: AsyncIterable[Any],
) -> AsyncIterator[Event]:
    """Process a stream and yield events."""
```

#### process_chunk

```python
async def process_chunk(self, chunk: str) -> list[Event]:
    """Process a single text chunk and return events."""
```

#### finalize

```python
async def finalize(self) -> list[Event]:
    """Finalize processing and return any remaining events."""
```

## Registry

Block type registry with validation support.

```python
from hother.streamblocks import Registry, Block, BaseMetadata, BaseContent
from typing import Literal

class TaskMetadata(BaseMetadata):
    block_type: Literal["task"] = "task"
    priority: str = "normal"

class TaskContent(BaseContent):
    pass

TaskBlock = Block[TaskMetadata, TaskContent]

# Create registry and register block types
registry = Registry()
registry.register("task", TaskBlock)
```

### Constructor Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str \| None` | `None` | Registry name |
| `failure_mode` | `MetadataValidationFailureMode` | `REJECT` | Validation failure behavior |

### Methods

#### register

```python
def register(
    self,
    block_type: str,
    block_class: type[Block],
) -> None:
    """Register a block type with its class."""
```

#### get

```python
def get(self, block_type: str) -> type[Block] | None:
    """Get the block class for a type."""
```

#### validate

```python
def validate(
    self,
    block_type: str,
    metadata: dict,
    content: str,
) -> ValidationResult:
    """Validate block data against registered type."""
```

## StreamState

Processing state enumeration.

```python
from hother.streamblocks import StreamState

StreamState.IDLE       # Not processing
StreamState.STREAMING  # Processing stream
StreamState.FINALIZING # Finalizing stream
StreamState.COMPLETED  # Stream completed
StreamState.ERROR      # Error occurred
```

## ValidationResult

Validation outcome with errors.

```python
from hother.streamblocks import ValidationResult

result = registry.validate("task", metadata, content)

if result.success:
    print("Validation passed")
else:
    print(f"Errors: {result.errors}")
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `success` | `bool` | Whether validation passed |
| `errors` | `list[str]` | List of error messages |
| `metadata` | `BaseMetadata \| None` | Validated metadata |
| `content` | `BaseContent \| None` | Validated content |

## MetadataValidationFailureMode

Validation failure behavior enumeration.

```python
from hother.streamblocks import MetadataValidationFailureMode

MetadataValidationFailureMode.REJECT    # Reject block on failure
MetadataValidationFailureMode.FALLBACK  # Use fallback metadata
MetadataValidationFailureMode.SKIP      # Skip validation
```

## Base Types

### BaseMetadata

Base metadata model with standard fields.

```python
from hother.streamblocks import BaseMetadata

class TaskMetadata(BaseMetadata):
    block_type: Literal["task"] = "task"
    priority: str = "normal"
    tags: list[str] = []
```

Required fields:

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Block identifier |
| `block_type` | `str` | Type of the block |

### BaseContent

Base content model with raw content field.

```python
from hother.streamblocks import BaseContent

class TaskContent(BaseContent):
    @classmethod
    def parse(cls, raw_text: str) -> "TaskContent":
        """Custom parsing logic."""
        return cls(raw_content=raw_text.strip())
```

Required fields:

| Field | Type | Description |
|-------|------|-------------|
| `raw_content` | `str` | Raw unparsed content |

## Detection and Parse Results

### DetectionResult

Result from syntax detection attempt.

```python
from hother.streamblocks import DetectionResult

result = DetectionResult(
    is_opening=True,
    is_closing=False,
    is_metadata_boundary=False,
    metadata={"id": "task01", "block_type": "task"},
)
```

### ParseResult

Result from parsing attempt.

```python
from hother.streamblocks import ParseResult

result = ParseResult(
    success=True,
    metadata=metadata,
    content=content,
    error=None,
)
```

## API Reference

::: hother.streamblocks.core.processor.StreamBlockProcessor
    options:
      show_root_heading: true
      show_source: false
      members_order: source

::: hother.streamblocks.core.registry.Registry
    options:
      show_root_heading: true
      show_source: false
      members_order: source

::: hother.streamblocks.core.registry.ValidationResult
    options:
      show_root_heading: true
      show_source: false

::: hother.streamblocks.core.registry.MetadataValidationFailureMode
    options:
      show_root_heading: true
      show_source: false

::: hother.streamblocks.core.types.BaseMetadata
    options:
      show_root_heading: true
      show_source: false

::: hother.streamblocks.core.types.BaseContent
    options:
      show_root_heading: true
      show_source: false

::: hother.streamblocks.core.types.DetectionResult
    options:
      show_root_heading: true
      show_source: false

::: hother.streamblocks.core.types.ParseResult
    options:
      show_root_heading: true
      show_source: false
