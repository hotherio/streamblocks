#!/usr/bin/env python3
"""Example 07: Block Opened Event.

This example shows how to use BlockOpenedEvent to prepare UI elements
or resources BEFORE block content arrives.
"""

import asyncio
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


async def delayed_stream() -> AsyncGenerator[str]:
    """Stream with delays to show timing."""
    chunks = [
        "Some text...\n",
        "!!files:files_operations\n",  # Block opens here!
    ]

    for chunk in chunks:
        yield chunk
        await asyncio.sleep(0.1)

    # Simulate slow content arrival
    print("   [Simulating network delay...]")
    await asyncio.sleep(1.0)

    for chunk in ["src/app.py:C\n", "src/test.py:C\n", "!!end\n"]:
        yield chunk
        await asyncio.sleep(0.1)


async def main() -> None:
    """Run the example."""
    print("=" * 60)
    print("Example 07: BlockOpenedEvent")
    print("=" * 60)
    print()

    # Setup
    syntax = DelimiterPreambleSyntax()
    registry = Registry(syntax=syntax)
    registry.register("files_operations", FileOperations)
    processor = StreamBlockProcessor(registry)

    print("Processing stream (watch for BlockOpened event):")
    print()

    # Track active blocks
    active_blocks = {}

    async for event in processor.process_stream(delayed_stream()):
        if isinstance(event, BlockStartEvent):
            print("🟢 BlockOpened!")
            print(f"   Syntax: {event.syntax}")
            print(f"   Line: {event.start_line}")

            if event.inline_metadata:
                print(f"   Metadata: {event.inline_metadata}")

            # Prepare resources (e.g., create UI widget)
            active_blocks[event.start_line] = {
                "syntax": event.syntax,
                "content": [],
            }

            print("   → UI widget created")
            print("   → Waiting for content...")
            print()

        elif isinstance(event, TextDeltaEvent):
            # Accumulate content for active blocks
            if event.inside_block and active_blocks:
                line = next(iter(active_blocks.keys()))
                active_blocks[line]["content"].append(event.delta)
                print(f"   📝 Accumulating: {repr(event.delta)[:30]}")

        elif isinstance(event, BlockEndEvent):
            block = event.get_block()
            if block is None:
                continue
            print("\n✅ BlockExtracted:")
            print(block.model_dump_json(indent=2))

            # Clean up
            active_blocks.clear()
            print("   → UI widget finalized\n")

    print()
    print("✓ BlockOpened emitted immediately")
    print("✓ Prepare UI before content arrives")
    print("✓ Better UX with early feedback")


if __name__ == "__main__":
    asyncio.run(main())
