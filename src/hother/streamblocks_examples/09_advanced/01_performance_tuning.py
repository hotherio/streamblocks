#!/usr/bin/env python3
"""Performance tuning with ProcessorConfig options."""

# --8<-- [start:imports]
import asyncio
import time
from textwrap import dedent

from hother.streamblocks import DelimiterFrontmatterSyntax, Registry, StreamBlockProcessor
from hother.streamblocks.core.processor import ProcessorConfig
from hother.streamblocks_examples.blocks.agent.files import FileOperations
from hother.streamblocks_examples.helpers.simulator import chunked_text_stream

# --8<-- [end:imports]


# --8<-- [start:benchmark]
async def benchmark_config(
    config: ProcessorConfig,
    stream_generator,
    name: str,
) -> tuple[int, float]:
    """Run benchmark with given config and return event count and duration."""
    syntax = DelimiterFrontmatterSyntax()
    registry = Registry(syntax=syntax)
    registry.register("files_operations", FileOperations)
    processor = StreamBlockProcessor(registry, config=config)

    event_count = 0
    start = time.perf_counter()

    async for _ in processor.process_stream(stream_generator()):
        event_count += 1

    duration = time.perf_counter() - start
    print(f"{name}: {event_count} events in {duration:.4f}s")
    return event_count, duration


# --8<-- [end:benchmark]


# --8<-- [start:main]
async def main() -> None:
    """Compare different ProcessorConfig settings."""
    # --8<-- [start:test_data]
    # Generate a large stream with multiple blocks
    block_template = dedent("""
        !!start
        ---
        id: ops{n:03d}
        block_type: files_operations
        ---
        src/file{n:03d}.py:C
        !!end
    """).strip()

    full_text = "\n\n".join(block_template.format(n=i) for i in range(20))

    # Character-by-character streaming simulation
    def stream():
        return chunked_text_stream(full_text, chunk_size=1, delay=0.0)

    # --8<-- [end:test_data]

    print("=== Performance Comparison ===\n")

    # --8<-- [start:configs]
    # Config 1: All events (default)
    config_all = ProcessorConfig(
        emit_text_deltas=True,
        emit_original_events=True,
        emit_section_end_events=True,
    )
    await benchmark_config(config_all, stream, "All events      ")

    # Config 2: No text deltas (fewer events)
    config_no_deltas = ProcessorConfig(
        emit_text_deltas=False,
        emit_original_events=True,
        emit_section_end_events=True,
    )
    await benchmark_config(config_no_deltas, stream, "No text deltas  ")

    # Config 3: Blocks only (minimal events)
    config_minimal = ProcessorConfig(
        emit_text_deltas=False,
        emit_original_events=False,
        emit_section_end_events=False,
    )
    await benchmark_config(config_minimal, stream, "Minimal (blocks)")
    # --8<-- [end:configs]

    # --8<-- [start:recommendations]
    print("\n=== Recommendations ===")
    print("- emit_text_deltas=False: Skip per-character events (big reduction)")
    print("- emit_original_events=False: Skip raw stream events")
    print("- emit_section_end_events=False: Skip metadata/content end events")
    print("\nUse minimal config for batch processing, full config for live UIs")
    # --8<-- [end:recommendations]


# --8<-- [end:main]


if __name__ == "__main__":
    asyncio.run(main())
