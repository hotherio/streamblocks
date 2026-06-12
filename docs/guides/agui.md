# AG-UI Protocol

Consume and emit [AG-UI](https://docs.ag-ui.com/) protocol events with bidirectional adapters.

AG-UI is an event-based protocol for agent-to-frontend communication. The `hother.streamblocks.extensions.agui` extension lets you run an AG-UI event stream through StreamBlocks: text events are scanned for blocks, every other event (lifecycle, tool calls, state) passes through untouched.

The extension requires the `ag-ui-protocol` package:

```bash
pip install ag-ui-protocol
```

```python
--8<-- "src/hother/streamblocks_examples/06_integrations/02_agui_integration.py:imports"
```

## Choose a direction

| Factory | Input | Output |
| --- | --- | --- |
| `create_agui_processor(registry)` | AG-UI events | Native StreamBlocks events |
| `create_agui_bidirectional_processor(registry, event_filter=...)` | AG-UI events | AG-UI events (dicts) |

Both factories return a pre-configured `ProtocolStreamProcessor` wired with `AGUIInputAdapter` on the input side.

## Unidirectional: AG-UI in, StreamBlocks events out

Use this when your own code sits at the end of the pipeline and wants typed StreamBlocks events:

```python
--8<-- "src/hother/streamblocks_examples/06_integrations/02_agui_integration.py:unidirectional"
```

The input adapter extracts text from `TEXT_MESSAGE_CONTENT` and `TEXT_MESSAGE_CHUNK` events and treats `RUN_FINISHED` as end of stream.

## Bidirectional: AG-UI in, AG-UI out

Use this when the output goes back to an AG-UI frontend. StreamBlocks events are converted to AG-UI `CUSTOM` events (emitted as dicts, so `ag-ui-protocol` is not needed at runtime on the consumer side), while original AG-UI events pass through unchanged:

```d2
direction: right

agui_in: AG-UI stream
input: AGUIInputAdapter
proc: StreamBlockProcessor
output: AGUIOutputAdapter
agui_out: AG-UI events

agui_in -> input: TEXT_MESSAGE_CONTENT
input -> proc: extracted text
input -> output: passthrough (non-text events) {style.stroke-dash: 3}
proc -> output: StreamBlocks events
output -> agui_out: "CUSTOM streamblocks.*"
```

```python
--8<-- "src/hother/streamblocks_examples/06_integrations/02_agui_integration.py:bidirectional"
```

[View source on GitHub](https://github.com/hotherio/streamblocks/tree/main/src/hother/streamblocks_examples/06_integrations/02_agui_integration.py)

The `AGUIOutputAdapter` maps StreamBlocks events to AG-UI as follows:

| StreamBlocks event | AG-UI event |
| --- | --- |
| `TextDeltaEvent`, `TextContentEvent` | `TEXT_MESSAGE_CONTENT` |
| `BlockStartEvent` | `CUSTOM` (`streamblocks.block_start`) |
| `BlockHeaderDeltaEvent`, `BlockMetadataDeltaEvent`, `BlockContentDeltaEvent` | `CUSTOM` (`streamblocks.block_delta`) |
| `BlockEndEvent` | `CUSTOM` (`streamblocks.block_end`) |
| `BlockErrorEvent` | `CUSTOM` (`streamblocks.block_error`) |

Block payloads travel in the event's `value` field (block id, syntax, metadata, content, line range, and so on).

## Filtering with AGUIEventFilter

`AGUIEventFilter` is a `Flag` enum controlling which StreamBlocks events the bidirectional processor emits. Presets:

| Preset | Emits |
| --- | --- |
| `ALL` (default) | Every StreamBlocks event. |
| `BLOCKS_ONLY` | Block lifecycle only: start, end, error. |
| `BLOCKS_WITH_PROGRESS` | Block lifecycle plus per-section delta events. |
| `TEXT_AND_FINAL` | Text deltas plus final block results (end, error). |
| `NONE` | No StreamBlocks events; passthrough only. |

Because it is a flag enum, you can also combine the fine-grained members (such as `RAW_TEXT`, `TEXT_DELTA`, and `BLOCK_DELTA`) with `|` to build a custom filter; see the [extensions reference](../reference/extensions.md) for the full list:

```python
processor = create_agui_bidirectional_processor(
    registry,
    event_filter=AGUIEventFilter.BLOCKS_WITH_PROGRESS,
)
```

Filtering applies to StreamBlocks events only; passthrough AG-UI events are always forwarded.

## Auto-detection

Importing `hother.streamblocks.extensions.agui` registers `AGUIInputAdapter` for adapter auto-detection (it claims events from the `ag_ui.` module namespace). A plain `ProtocolStreamProcessor` with `auto_detect_adapter` enabled will then recognize an AG-UI stream from its first event without explicit wiring.

## Next steps

- [Events](../reference/events.md): the StreamBlocks events behind each `CUSTOM` mapping.
- [Extensions reference](../reference/extensions.md): full API for the AG-UI adapters and filter flags.
- [Performance Tuning](performance.md): reduce event volume before it reaches the frontend.
