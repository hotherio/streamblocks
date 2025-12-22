#!/usr/bin/env python3
"""Example 10: Callable Adapter (Quick Custom Extraction).

This example shows how to use CallableAdapter for quick custom
extraction without creating a full adapter class.
"""

import asyncio
from collections.abc import AsyncGenerator
from typing import Any

from hother.streamblocks import (
    BlockEndEvent,
    CallableAdapter,
    DelimiterPreambleSyntax,
    Registry,
    StreamBlockProcessor,
)
from hother.streamblocks.blocks import FileOperations


# Simple dict-based chunks
async def dict_stream() -> AsyncGenerator[dict[str, Any]]:
    """Stream of dictionaries."""
    chunks = [
        {"content": "!!files:files_operations\n", "id": 1},
        {"content": "app.py:C\n", "id": 2},
        {"content": "test.py:C\n", "id": 3},
        {"content": "!!end\n", "id": 4, "done": True},
    ]

    for chunk in chunks:
        yield chunk
        await asyncio.sleep(0.1)


async def main() -> None:
    """Run the example."""
    print("=" * 60)
    print("Example 10: CallableAdapter (Quick & Easy)")
    print("=" * 60)
    print()

    # Create adapter with lambda functions
    adapter = CallableAdapter(
        # Extract text from 'content' key
        extract_fn=lambda chunk: chunk.get("content"),
        # Check 'done' flag for completion
        is_complete_fn=lambda chunk: chunk.get("done", False),
        # Extract ID as metadata
        metadata_fn=lambda chunk: {"chunk_id": chunk.get("id")},
    )

    # Setup
    syntax = DelimiterPreambleSyntax()
    registry = Registry(syntax=syntax)
    registry.register("files_operations", FileOperations)
    processor = StreamBlockProcessor(registry)

    print("Processing dict stream with CallableAdapter...")
    print()

    async for event in processor.process_stream(dict_stream(), adapter=adapter):
        # Original dicts
        if isinstance(event, dict):
            print(f"📦 Dict Chunk: id={event['id']}, content={repr(event['content'])[:30]}")
            if event.get("done"):
                print("   🏁 Final chunk!")

        # Blocks
        elif isinstance(event, BlockEndEvent):
            block = event.get_block()
            if block is None:
                continue
            print(f"\n✅ Block: {block.metadata.id}")
            for op in block.content.operations:
                print(f"   - {op.path}")
            print()

    print()
    print("✓ No adapter class needed")
    print("✓ Just provide lambda functions")
    print("✓ Perfect for quick prototyping")


if __name__ == "__main__":
    asyncio.run(main())
