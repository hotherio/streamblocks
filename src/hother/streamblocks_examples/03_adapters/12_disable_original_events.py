#!/usr/bin/env python3
"""Example 12: Disable Original Events (Lightweight Mode).

This example shows how to disable original event passthrough for
maximum performance and minimal overhead.
"""

import asyncio
from collections.abc import AsyncGenerator

from hother.streamblocks import (
    BlockEndEvent,
    DelimiterPreambleSyntax,
    Registry,
    StreamBlockProcessor,
    TextContentEvent,
    TextDeltaEvent,
)
from hother.streamblocks.core.processor import ProcessorConfig
from hother.streamblocks_examples.blocks.agent.files import FileOperations


# Mock Gemini chunk
class GeminiChunk:
    __module__ = "google.genai.types"

    def __init__(self, text: str) -> None:
        self.text = text
        self.size = len(text.encode())  # Simulate chunk size


async def large_gemini_stream() -> AsyncGenerator[GeminiChunk]:
    """Simulate large Gemini stream."""
    chunks = [
        "Creating project...\n",
        "!!files:files_operations\n",
        "src/main.py:C\n",
        "src/utils.py:C\n",
        "tests/test_main.py:C\n",
        "!!end\n",
        "Done!\n",
    ]

    for chunk in chunks:
        yield GeminiChunk(chunk)
        await asyncio.sleep(0.05)


async def compare_modes() -> None:
    """Compare normal vs lightweight mode."""

    print("=" * 60)
    print("Example 12: Lightweight Mode (No Original Events)")
    print("=" * 60)
    print()

    # Mode 1: Normal (with original events)
    print("Mode 1: Normal (emit_original_events=True)")
    print("-" * 40)

    syntax = DelimiterPreambleSyntax()
    registry = Registry(syntax=syntax)
    registry.register("files_operations", FileOperations)

    config_normal = ProcessorConfig(emit_original_events=True)  # Default
    processor_normal = StreamBlockProcessor(registry, config=config_normal)

    event_count_normal = 0
    async for event in processor_normal.process_stream(large_gemini_stream()):
        event_count_normal += 1
        if isinstance(event, GeminiChunk):
            print(f"  📦 GeminiChunk ({event.size} bytes)")
        elif isinstance(event, TextDeltaEvent):
            print("  📝 TextDelta")
        elif isinstance(event, BlockEndEvent):
            print("  ✅ Block")

    print(f"\nTotal events: {event_count_normal}")

    # Mode 2: Lightweight (without original events)
    print("\n" + "=" * 60)
    print("Mode 2: Lightweight (emit_original_events=False)")
    print("-" * 40)

    config_light = ProcessorConfig(emit_original_events=False)  # Disable passthrough
    processor_light = StreamBlockProcessor(registry, config=config_light)

    event_count_light = 0
    async for event in processor_light.process_stream(large_gemini_stream()):
        event_count_light += 1
        if isinstance(event, GeminiChunk):
            print("  📦 GeminiChunk (shouldn't see this!)")
        elif isinstance(event, TextDeltaEvent):
            print("  📝 TextDelta")
        elif isinstance(event, TextContentEvent):
            print("  💬 RawText")
        elif isinstance(event, BlockEndEvent):
            print("  ✅ Block")

    print(f"\nTotal events: {event_count_light}")

    # Summary
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    print(f"Normal mode events:      {event_count_normal}")
    print(f"Lightweight mode events: {event_count_light}")
    print(f"Reduction:               {event_count_normal - event_count_light} events")
    print(f"Savings:                 {((event_count_normal - event_count_light) / event_count_normal * 100):.1f}%")
    print()
    print("When to use lightweight mode:")
    print("  ✓ Don't need original chunks")
    print("  ✓ Only care about StreamBlocks events")
    print("  ✓ Maximum performance needed")
    print("  ✓ Batch processing")
    print()
    print("When to use normal mode:")
    print("  ✓ Need access to provider metadata")
    print("  ✓ Want complete transparency")
    print("  ✓ Debugging/logging original events")


if __name__ == "__main__":
    asyncio.run(compare_modes())
