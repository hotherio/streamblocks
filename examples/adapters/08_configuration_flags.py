#!/usr/bin/env python3
"""Example 08: Configuration Flags.

This example demonstrates all processor configuration options:
- emit_original_events
- emit_text_deltas
- auto_detect_adapter
"""

import asyncio
from collections.abc import AsyncGenerator

from hother.streamblocks import (
    BlockEndEvent,
    DelimiterPreambleSyntax,
    GeminiAdapter,
    Registry,
    StreamAdapter,
    StreamBlockProcessor,
    TextDeltaEvent,
)
from hother.streamblocks.blocks import FileOperations


# Mock Gemini chunk
class GeminiChunk:
    __module__ = "google.genai.types"

    def __init__(self, text: str) -> None:
        self.text = text


async def gemini_stream() -> AsyncGenerator[GeminiChunk]:
    """Simple Gemini stream."""
    for chunk in ["!!f:files_operations\n", "app.py:C\n", "!!end\n"]:
        yield GeminiChunk(chunk)
        await asyncio.sleep(0.05)


async def demo_config(name: str, adapter: StreamAdapter[GeminiChunk] | None = None, **config: bool) -> None:
    """Demo a specific configuration."""
    print(f"\n{'=' * 60}")
    print(f"Configuration: {name}")
    print(f"Settings: {config}")
    print("=" * 60)

    syntax = DelimiterPreambleSyntax()
    registry = Registry(syntax=syntax)
    registry.register("files_operations", FileOperations)
    processor = StreamBlockProcessor(registry, **config)

    events_seen = {"original": 0, "text_delta": 0, "block": 0}

    async for event in processor.process_stream(gemini_stream(), adapter=adapter):
        if isinstance(event, GeminiChunk):
            events_seen["original"] += 1
            print("  📦 Original chunk")
        elif isinstance(event, TextDeltaEvent):
            events_seen["text_delta"] += 1
            print("  📝 Text delta")
        elif isinstance(event, BlockEndEvent):
            events_seen["block"] += 1
            print("  ✅ Block extracted")

    print(
        f"\nEvents: Original={events_seen['original']}, "
        f"TextDelta={events_seen['text_delta']}, "
        f"Block={events_seen['block']}"
    )


async def main() -> None:
    """Run all configuration demos."""
    print("=" * 60)
    print("Example 08: Configuration Options")
    print("=" * 60)

    # Default configuration
    await demo_config(
        "Default (All Enabled)",
        emit_original_events=True,
        emit_text_deltas=True,
        auto_detect_adapter=True,
    )

    # Disable original events
    await demo_config(
        "No Original Events (Lightweight)",
        emit_original_events=False,
        emit_text_deltas=True,
        auto_detect_adapter=True,
    )

    # Disable text deltas
    await demo_config(
        "No Text Deltas (Line-based only)",
        emit_original_events=True,
        emit_text_deltas=False,
        auto_detect_adapter=True,
    )

    # Manual adapter (no auto-detect)
    await demo_config(
        "Manual Adapter (Explicit)",
        adapter=GeminiAdapter(),
        emit_original_events=True,
        emit_text_deltas=True,
        auto_detect_adapter=False,
    )

    # Minimal mode
    await demo_config(
        "Minimal Mode (Only Blocks)",
        emit_original_events=False,
        emit_text_deltas=False,
        auto_detect_adapter=True,
    )

    print("\n" + "=" * 60)
    print("Configuration Summary:")
    print("=" * 60)
    print("emit_original_events - Pass through original chunks")
    print("emit_text_deltas     - Real-time text streaming")
    print("auto_detect_adapter  - Auto-detect from first chunk")
    print("\nRecommendations:")
    print("- Default: Full transparency + real-time streaming")
    print("- Lightweight: Disable originals if not needed")
    print("- Performance: Disable deltas for batch processing")


if __name__ == "__main__":
    asyncio.run(main())
