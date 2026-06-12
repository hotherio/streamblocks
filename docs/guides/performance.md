# Performance Tuning

Tune processor configuration for throughput and memory.

All knobs live on `ProcessorConfig`, passed to the processor at construction time:

```python
--8<-- "src/hother/streamblocks_examples/09_advanced/01_performance_tuning.py:imports"
```

The full field-by-field table lives in the [architecture overview](../concepts/index.md#configuration); this guide focuses on the trade-offs.

## Measure the impact of event flags

Event emission dominates cost on fine-grained streams: with character-level chunking, `emit_text_deltas` produces one event per chunk. The benchmark below feeds the same 20-block stream through three configurations:

```python
--8<-- "src/hother/streamblocks_examples/09_advanced/01_performance_tuning.py:test_data"
```

```python
--8<-- "src/hother/streamblocks_examples/09_advanced/01_performance_tuning.py:configs"
```

[View source on GitHub](https://github.com/hotherio/streamblocks/tree/main/src/hother/streamblocks_examples/09_advanced/01_performance_tuning.py)

A representative run (character-by-character streaming):

```text
All events      : 1955 events in 0.0203s
No text deltas  : 357 events in 0.0065s
Minimal (blocks): 317 events in 0.0049s
```

Disabling text deltas alone removed over 80% of events here. The trade-off: without `TextDeltaEvent` you lose character-level updates for live UIs; block events still fire as usual.

## Size limits

`max_block_size` and `max_line_length` are safety valves against malformed or adversarial streams:

- A block that grows past `max_block_size` is rejected and surfaces as a `BlockErrorEvent` with error code `SIZE_EXCEEDED`: the stream keeps going.
- A line longer than `max_line_length` is truncated rather than buffered indefinitely.

Raise them when you legitimately stream large blocks (e.g. whole files as block content):

```python
config = ProcessorConfig(max_block_size=2_097_152)  # 2 MB
```

Keep them tight for untrusted input to bound memory per block.

## Tips for high-throughput streams

```python
--8<-- "src/hother/streamblocks_examples/09_advanced/01_performance_tuning.py:recommendations"
```

- Start from the minimal config (`emit_text_deltas=False`, `emit_original_events=False`, `emit_section_end_events=False`) for batch processing; enable flags one by one as features need them.
- Set `auto_detect_adapter=False` when feeding plain `str` chunks: it skips first-chunk detection and uses the identity adapter directly.
- Prefer larger upstream chunks over character-level streaming when latency allows; fewer chunks means fewer delta events and fewer accumulator passes.
- Keep your event loop body cheap: the `async for` consumer is on the hot path, so defer heavy work (I/O, rendering) to tasks or queues.

## Next steps

- [Events](../reference/events.md): exactly which events each flag controls.
- [Error Handling](error-handling.md): handling `SIZE_EXCEEDED` and other block errors.
- [Logging](logging.md): observe processor behavior without adding events.
