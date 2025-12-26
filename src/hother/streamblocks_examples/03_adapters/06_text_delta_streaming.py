#!/usr/bin/env python3
"""Example 06: Real-Time Text Delta Streaming.

This example shows character-by-character streaming with TextDeltaEvent.
Perfect for typewriter effects or live progress indicators.
"""

import asyncio
import sys
from collections.abc import AsyncGenerator

from hother.streamblocks import (
    BlockEndEvent,
    BlockStartEvent,
    DelimiterPreambleSyntax,
    Registry,
    StreamBlockProcessor,
    TextDeltaEvent,
)
from hother.streamblocks_examples.blocks.agent.files import FileOperations


async def character_stream() -> AsyncGenerator[str]:
    """Stream text character by character."""
    text = (
        "Creating project structure...\n"
        "!!files:files_operations\n"
        "src/main.py:C\n"
        "src/utils.py:C\n"
        "tests/test_main.py:C\n"
        "!!end\n"
        "Done!\n"
    )

    # Stream character by character
    for char in text:
        yield char
        await asyncio.sleep(0.02)  # Slow for visual effect


async def main() -> None:
    """Run the example."""
    print("=" * 60)
    print("Example 06: Real-Time Text Streaming (Typewriter Effect)")
    print("=" * 60)
    print()

    # Setup
    syntax = DelimiterPreambleSyntax()
    registry = Registry(syntax=syntax)
    registry.register("files_operations", FileOperations)
    processor = StreamBlockProcessor(registry)

    print("Streaming text in real-time:")
    print("-" * 40)

    async for event in processor.process_stream(character_stream()):
        if isinstance(event, TextDeltaEvent):
            # Print each character immediately (typewriter effect)
            sys.stdout.write(event.delta)
            sys.stdout.flush()

            # Show context
            if event.inside_block:
                context = f" [{event.section}]"
                # Clear the context indicator on newlines
                if event.delta == "\n":
                    sys.stdout.write(f"  {context}\n")

        elif isinstance(event, BlockStartEvent):
            sys.stdout.write(f"\n[Block starting: {event.syntax}]\n")

        elif isinstance(event, BlockEndEvent):
            block = event.get_block()
            if block is None:
                continue
            print("\n[Block extracted:]")
            print(block.model_dump_json(indent=2))

    print("-" * 40)
    print()
    print("✓ Character-by-character streaming")
    print("✓ Inside/outside block tracking")
    print("✓ Perfect for live UIs")


if __name__ == "__main__":
    asyncio.run(main())
