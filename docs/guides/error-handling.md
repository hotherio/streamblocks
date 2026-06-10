# Error Handling

When a block cannot be extracted, the processor does not raise — it emits a `BlockErrorEvent` and keeps processing the stream. This guide covers the event's structure, the error codes, and the size limits that can trigger rejection.

## BlockErrorEvent

| Field | Type | Description |
|-------|------|-------------|
| `block_id` | `str \| None` | Block identifier, when known |
| `reason` | `str` | Human-readable failure description |
| `error_code` | `BlockErrorCode \| None` | Machine-readable category (table below) |
| `syntax` | `str` | Syntax that was accumulating the block |
| `start_line` / `end_line` | `int` / `int \| None` | Where the failed block started and ended |
| `exception` | `Exception \| None` | The original exception object, when one was raised |

## Error codes

`BlockErrorCode` categorizes every failure:

| Code | Meaning |
|------|---------|
| `VALIDATION_FAILED` | Block structure is valid, but a syntax or registry [validator](validation.md) rejected it |
| `SIZE_EXCEEDED` | Block grew past `max_block_size`; rejected to prevent memory exhaustion |
| `UNCLOSED_BLOCK` | Block opened but never closed before the stream ended |
| `UNKNOWN_TYPE` | The syntax extracted a `block_type` that is not registered |
| `PARSE_FAILED` | Parsing failed — malformed YAML, invalid structure, or a `parse()` exception |
| `MISSING_METADATA` | Parse succeeded but returned no metadata |
| `MISSING_CONTENT` | Parse succeeded but returned no content |
| `SYNTAX_ERROR` | Syntax-specific custom validation failure |

Branch on the code for recovery logic:

```python
from hother.streamblocks import BlockErrorCode, BlockErrorEvent

async for event in processor.process_stream(stream):
    if isinstance(event, BlockErrorEvent):
        if event.error_code == BlockErrorCode.SIZE_EXCEEDED:
            logger.warning("block too large: %s", event.reason)
        elif event.error_code == BlockErrorCode.UNCLOSED_BLOCK:
            logger.info("incomplete block at stream end: %s", event.reason)
        else:
            logger.error("block rejected: %s", event.reason)
```

## Inspecting the original exception

`event.exception` preserves the underlying error object, so you can handle YAML scanner errors, Pydantic validation errors, and type errors differently:

```python
--8<-- "src/hother/streamblocks_examples/01_basics/03_error_handling.py:setup"
```

```python
--8<-- "src/hother/streamblocks_examples/01_basics/03_error_handling.py:handling"
```

For Pydantic `ValidationError`, `event.exception.errors()` lists exactly which metadata fields are missing or invalid. The full runnable script is in [Basics examples](../examples/basics.md).

## Unclosed blocks at stream end

If a stream finishes while a block is still accumulating (the LLM was cut off, or never emitted the closing marker), the pending candidate is flushed as a `BlockErrorEvent` with code `UNCLOSED_BLOCK` and reason `"Stream ended without closing marker"`. The accumulated lines are discarded rather than re-emitted as text, so treat this code as "partial block": `start_line` and `end_line` tell you which part of the stream was consumed by it.

## Size limits

Two `ProcessorConfig` limits protect against runaway blocks:

| Option | Default | Behavior when exceeded |
|--------|---------|------------------------|
| `max_block_size` | `1_048_576` (1 MiB) | Block rejected with `SIZE_EXCEEDED` |
| `max_line_length` | `16_384` (16 KiB) | Line truncated to the limit |

```python
from hother.streamblocks.core.processor import ProcessorConfig

config = ProcessorConfig(max_block_size=2_097_152)  # 2 MiB
processor = StreamBlockProcessor(registry, config=config)
```

## Next steps

- [Validation](validation.md) — reject bad blocks early, before content accumulates.
- [Events](../concepts/events.md) — where `BlockErrorEvent` fits in the event stream.
- [Performance Tuning](performance.md) — the remaining `ProcessorConfig` options.
