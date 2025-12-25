# Performance

This guide covers performance optimization for Streamblocks.

## Event Filtering

Disable events you don't need:

```python
# Only emit block events (skip text deltas)
processor = StreamBlockProcessor(
    emit_text_delta=False,
    emit_block_events=True,
)

# Only emit final blocks (skip updates)
processor = StreamBlockProcessor(
    emit_block_opened=False,
    emit_block_updated=False,
    emit_block_closed=True,
)
```

## Buffer Management

Configure buffer sizes for your use case:

```python
from hother.streamblocks.core.processor import ProcessorConfig

config = ProcessorConfig(max_block_size=1_000_000)  # Maximum block content size
processor = StreamBlockProcessor(registry, config=config)
```

## Async Processing

Use async for I/O-bound operations:

```python
async def process_multiple_streams(streams):
    tasks = [process_stream(s) for s in streams]
    results = await asyncio.gather(*tasks)
    return results
```

## Memory Efficiency

For large streams, process events immediately:

```python
async for event in processor.process_stream(stream):
    # Process and discard - don't accumulate
    handle_event(event)
```

## Profiling

Profile your Streamblocks usage:

```python
import cProfile
import pstats

with cProfile.Profile() as pr:
    asyncio.run(process_stream(stream))

stats = pstats.Stats(pr)
stats.sort_stats('cumulative')
stats.print_stats(10)
```

## Benchmarks

Typical performance characteristics:

| Scenario | Throughput |
|----------|------------|
| Plain text pass-through | ~100 MB/s |
| Simple block extraction | ~50 MB/s |
| Complex nested parsing | ~10 MB/s |

*Actual performance depends on syntax complexity and hardware.*
