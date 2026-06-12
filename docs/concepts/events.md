# Events

Everything the processor sees becomes an event: stream lifecycle, text outside blocks, and every stage of a block's life. This page is the authoritative map of the event model.

## Consuming events

All events are immutable Pydantic models deriving from `BaseEvent`. The `Event` type is a discriminated union (on the `type` field) of every concrete event class, so the idiomatic consumption pattern is one `isinstance` check per class you care about:

```python
--8<-- "src/hother/streamblocks_examples/03_adapters/14_section_delta_events.py:example"
```

[View source on GitHub](https://github.com/hotherio/streamblocks/tree/main/src/hother/streamblocks_examples/03_adapters/14_section_delta_events.py)

Every event shares three fields from `BaseEvent`:

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | `int` | Unix timestamp in milliseconds, auto-generated |
| `event_id` | `str` | Unique identifier (UUID), auto-generated |
| `raw_event` | `Any \| None` | Original provider event, preserved by [adapters](adapters.md) |

The per-event tables below list only the fields each event adds.

!!! note "Native provider events in the stream"
    `StreamBlockProcessor.process_stream()` yields `TChunk | Event`: when `emit_original_events=True` (the default), the original provider chunks are interleaved with StreamBlocks events. Use `processor.is_native_event(event)` to tell them apart without coupling to a provider.

## Event flow for one block

For each block, events arrive in a fixed order. Which sections appear depends on the [syntax](syntaxes.md): frontmatter syntaxes have a metadata section, the preamble syntax carries metadata inline in the header.

```d2
shape: sequence_diagram

llm: LLM stream
proc: Processor
app: Your app

llm -> proc: "!!plan01:task"
proc -> app: BLOCK_START
proc -> app: BLOCK_HEADER_DELTA
llm -> proc: metadata lines
proc -> app: BLOCK_METADATA_DELTA
proc -> app: "BLOCK_METADATA_END (parsed, validated)"
llm -> proc: content lines
proc -> app: BLOCK_CONTENT_DELTA
proc -> app: BLOCK_CONTENT_END
llm -> proc: "!!end"
proc -> app: "BLOCK_END (typed block)"
```

A block can also fail earlier, for example `BLOCK_ERROR` with `UNCLOSED_BLOCK` at end of stream, or with `VALIDATION_FAILED` right after `BLOCK_METADATA_END` when early metadata validation aborts the block.

## Overview

| `EventType` | Event class | Emitted when |
|-------------|-------------|--------------|
| `STREAM_STARTED` | [`StreamStartedEvent`](#streamstartedevent) | Stream processing begins |
| `STREAM_FINISHED` | [`StreamFinishedEvent`](#streamfinishedevent) | Stream completes |
| `STREAM_ERROR` | [`StreamErrorEvent`](#streamerrorevent) | Stream processing fails |
| `TEXT_CONTENT` | [`TextContentEvent`](#textcontentevent) | A complete line outside any block |
| `TEXT_DELTA` | [`TextDeltaEvent`](#textdeltaevent) | A raw text chunk, before line completion |
| `BLOCK_START` | [`BlockStartEvent`](#blockstartevent) | Block opening marker detected |
| `BLOCK_HEADER_DELTA` | [`BlockHeaderDeltaEvent`](#section-delta-events) | Content added to the header section |
| `BLOCK_METADATA_DELTA` | [`BlockMetadataDeltaEvent`](#section-delta-events) | Content added to the metadata section |
| `BLOCK_CONTENT_DELTA` | [`BlockContentDeltaEvent`](#section-delta-events) | Content added to the content section |
| `BLOCK_METADATA_END` | [`BlockMetadataEndEvent`](#blockmetadataendevent) | Metadata section complete and parsed |
| `BLOCK_CONTENT_END` | [`BlockContentEndEvent`](#blockcontentendevent) | Content section complete and parsed |
| `BLOCK_END` | [`BlockEndEvent`](#blockendevent) | Block extracted and validated |
| `BLOCK_ERROR` | [`BlockErrorEvent`](#blockerrorevent) | Block extraction failed |
| `CUSTOM` | [`CustomEvent`](#customevent) | Application-specific events |

## Lifecycle events

### StreamStartedEvent

First event of every stream.

| Field | Type | Description |
|-------|------|-------------|
| `stream_id` | `str` | Identifier of this stream |
| `registry_name` | `str \| None` | Name of the registry in use |

### StreamFinishedEvent

Last event of a successful stream, with summary counters.

| Field | Type | Description |
|-------|------|-------------|
| `stream_id` | `str` | Identifier of this stream |
| `blocks_extracted` | `int` | Successfully extracted blocks |
| `blocks_rejected` | `int` | Rejected blocks |
| `total_events` | `int` | Total events emitted |
| `duration_ms` | `int \| None` | Processing duration |

### StreamErrorEvent

Stream-level failure (not a single block failing).

| Field | Type | Description |
|-------|------|-------------|
| `stream_id` | `str` | Identifier of this stream |
| `error` | `str` | Error description |
| `error_code` | `str \| None` | Optional machine-readable code |

## Text events

### TextContentEvent

A complete line of text outside any block. Nothing in the stream is lost: prose between blocks arrives here.

| Field | Type | Description |
|-------|------|-------------|
| `content` | `str` | The line content |
| `line_number` | `int` | Line position in the stream |

### TextDeltaEvent

Emitted immediately as text arrives, before lines complete. Each delta knows whether it is inside a block and which section it belongs to, ideal for typewriter effects and live UIs:

| Field | Type | Description |
|-------|------|-------------|
| `delta` | `str` | The raw text chunk |
| `inside_block` | `bool` | Whether the chunk falls inside a block |
| `block_id` | `str \| None` | Owning block, if inside one |
| `section` | `str \| None` | `"header"`, `"metadata"`, or `"content"` |

```python
--8<-- "src/hother/streamblocks_examples/03_adapters/06_text_delta_streaming.py:example"
```

[View source on GitHub](https://github.com/hotherio/streamblocks/tree/main/src/hother/streamblocks_examples/03_adapters/06_text_delta_streaming.py)

## Block events

### BlockStartEvent

Fires as soon as the opening marker is detected, before any content. Use it to create UI elements or allocate resources early:

| Field | Type | Description |
|-------|------|-------------|
| `block_id` | `str` | Block identifier |
| `block_type` | `str \| None` | Type, if already known from the opening line |
| `syntax` | `str` | Detecting syntax name |
| `start_line` | `int` | Line where the block opened |
| `inline_metadata` | `dict \| None` | Metadata parsed from the opening line (preamble syntax) |

```python
--8<-- "src/hother/streamblocks_examples/03_adapters/07_block_opened_event.py:example"
```

[View source on GitHub](https://github.com/hotherio/streamblocks/tree/main/src/hother/streamblocks_examples/03_adapters/07_block_opened_event.py)

### Section delta events

`BlockHeaderDeltaEvent`, `BlockMetadataDeltaEvent`, and `BlockContentDeltaEvent` stream a block's three sections as they accumulate. All three share:

| Field | Type | Description |
|-------|------|-------------|
| `block_id` | `str` | Owning block |
| `delta` | `str` | Text added to the section |
| `syntax` | `str` | Detecting syntax name |
| `current_line` | `int` | Current line number |
| `accumulated_size` | `int` | Bytes accumulated so far (drives `max_block_size`) |

Per-event extras:

| Event | Extra field | Description |
|-------|-------------|-------------|
| `BlockHeaderDeltaEvent` | `inline_metadata: dict \| None` | Metadata parsed from the header line |
| `BlockMetadataDeltaEvent` | `is_boundary: bool` | Whether this delta is a `---` boundary line |
| `BlockContentDeltaEvent` | none | |

### BlockMetadataEndEvent

Fires when the metadata section completes, before content begins. This enables early validation: combined with `MetadataValidationFailureMode.ABORT_BLOCK`, a failing metadata validator aborts the block before its content streams in (see the [Validation guide](../guides/validation.md)).

| Field | Type | Description |
|-------|------|-------------|
| `block_id` | `str` | Owning block |
| `syntax` | `str` | Detecting syntax name |
| `start_line` / `end_line` | `int` | Section bounds |
| `raw_metadata` | `str` | Raw metadata text |
| `parsed_metadata` | `dict \| None` | Parsed metadata |
| `validation_passed` | `bool` | Early validation outcome |
| `validation_error` | `str \| None` | Failure detail |

```python
--8<-- "src/hother/streamblocks_examples/03_adapters/15_section_end_events.py:metadata_end"
```

[View source on GitHub](https://github.com/hotherio/streamblocks/tree/main/src/hother/streamblocks_examples/03_adapters/15_section_end_events.py)

### BlockContentEndEvent

Mirror of the metadata end event for the content section, emitted just before final extraction.

| Field | Type | Description |
|-------|------|-------------|
| `block_id` | `str` | Owning block |
| `syntax` | `str` | Detecting syntax name |
| `start_line` / `end_line` | `int` | Section bounds |
| `raw_content` | `str` | Raw content text |
| `parsed_content` | `dict \| None` | Parsed content |
| `validation_passed` | `bool` | Early validation outcome |
| `validation_error` | `str \| None` | Failure detail |

### BlockEndEvent

The block was extracted and validated. `get_block()` returns the typed `ExtractedBlock`.

| Field | Type | Description |
|-------|------|-------------|
| `block_id` | `str` | Block identifier |
| `block_type` | `str` | Registered block type |
| `syntax` | `str` | Detecting syntax name |
| `start_line` / `end_line` | `int` | Block bounds in the stream |
| `metadata` | `dict` | Extracted metadata (serializable form) |
| `content` | `dict` | Extracted content (serializable form) |
| `raw_content` | `str` | Original unparsed body |
| `hash_id` | `str` | Stable hash for deduplication/caching |

### BlockErrorEvent

Block extraction failed; the stream keeps processing. `error_code` values are covered in the [Error Handling guide](../guides/error-handling.md).

| Field | Type | Description |
|-------|------|-------------|
| `block_id` | `str \| None` | Block identifier, if known |
| `reason` | `str` | Human-readable failure reason |
| `error_code` | `BlockErrorCode \| None` | `VALIDATION_FAILED`, `SIZE_EXCEEDED`, `UNCLOSED_BLOCK`, ... |
| `syntax` | `str` | Detecting syntax name |
| `start_line` / `end_line` | `int` / `int \| None` | Block bounds |
| `exception` | `Exception \| None` | Original exception (excluded from serialization) |

## Custom events

### CustomEvent

Application-specific events, also used by the [AG-UI output adapter](../guides/agui.md) to wrap block events.

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Event name (e.g. `streamblocks.block_end`) |
| `value` | `dict` | Arbitrary payload |

## Controlling event volume

Three `ProcessorConfig` flags gate event emission (all default to `True`):

| Flag | Gates | Disable when |
|------|-------|--------------|
| `emit_original_events` | Passthrough of native provider chunks | You only need StreamBlocks events |
| `emit_text_deltas` | `TextDeltaEvent` | Batch processing; line-level events suffice |
| `emit_section_end_events` | `BlockMetadataEndEvent`, `BlockContentEndEvent` | No early validation needed |

```python
--8<-- "src/hother/streamblocks_examples/03_adapters/15_section_end_events.py:optout"
```

See [Performance Tuning](../guides/performance.md) for the trade-offs, and the [configuration flags example](https://github.com/hotherio/streamblocks/tree/main/src/hother/streamblocks_examples/03_adapters/08_configuration_flags.py) for all combinations in action.

## Next steps

- [Adapters](adapters.md): how provider chunks become text and events.
- [Error Handling](../guides/error-handling.md): reacting to `BlockErrorEvent` codes.
- [Events reference](../reference/events.md): full API of every event class.
