#!/usr/bin/env python3
"""Example 10: Simple Inline Adapter.

This example shows how to create a simple inline input adapter class
for quick custom extraction without a full adapter class.
"""

import asyncio
from typing import Any

from hother.streamblocks import (
    BlockEndEvent,
    DelimiterPreambleSyntax,
    EventCategory,
    Registry,
    StreamBlockProcessor,
)
from hother.streamblocks_examples.blocks.agent.files import FileOperations


# Simple dict-based chunks
async def dict_stream():
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


# Simple inline adapter class
class DictInputAdapter:
    """Simple adapter for dict-based chunks."""

    def categorize(self, event: dict[str, Any]) -> EventCategory:
        """All dicts contain text content."""
        return EventCategory.TEXT_CONTENT

    def extract_text(self, chunk: dict[str, Any]) -> str | None:
        """Extract text from 'content' key."""
        return chunk.get("content")

    def is_complete(self, chunk: dict[str, Any]) -> bool:
        """Check 'done' flag for completion."""
        return chunk.get("done", False)

    def get_metadata(self, chunk: dict[str, Any]) -> dict[str, Any] | None:
        """Extract ID as metadata."""
        if "id" in chunk:
            return {"chunk_id": chunk.get("id")}
        return None


async def main() -> None:
    """Run the example."""
    print("=" * 60)
    print("Example 10: Simple Inline Adapter")
    print("=" * 60)
    print()

    # Create adapter instance
    adapter = DictInputAdapter()

    # Setup
    syntax = DelimiterPreambleSyntax()
    registry = Registry(syntax=syntax)
    registry.register("files_operations", FileOperations)
    processor = StreamBlockProcessor(registry)

    print("Processing dict stream with inline adapter...")
    print()

    async for event in processor.process_stream(dict_stream(), adapter=adapter):
        # Original dicts
        if isinstance(event, dict):
            print(f"Dict Chunk: id={event['id']}, content={repr(event['content'])[:30]}")
            if event.get("done"):
                print("   Final chunk!")

        # Blocks
        elif isinstance(event, BlockEndEvent):
            block = event.get_block()
            if block is None:
                continue
            print("\nBlock Extracted:")
            print(block.model_dump_json(indent=2))
            print()

    print()
    print("Simple adapter class")
    print("Just implement: categorize, extract_text, is_complete, get_metadata")
    print("Perfect for quick prototyping")


if __name__ == "__main__":
    asyncio.run(main())
