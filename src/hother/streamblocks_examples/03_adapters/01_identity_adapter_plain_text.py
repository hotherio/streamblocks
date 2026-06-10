#!/usr/bin/env python3
"""Example 01: Plain Text Stream (Identity Adapter).

This example shows the default behavior with plain text streams.
No adapter needed - it just works!
"""

# --8<-- [start:imports]
import asyncio
from collections.abc import AsyncGenerator

from hother.streamblocks import BlockEndEvent, Registry, StreamBlockProcessor, TextContentEvent, TextDeltaEvent
from hother.streamblocks_examples.blocks.agent.files import FileOperations

# --8<-- [end:imports]


# --8<-- [start:stream]
async def plain_text_stream() -> AsyncGenerator[str]:
    """Simulate a plain text stream."""
    chunks = [
        "Some text before the block\n",
        "!!files01:files_operations\n",
        "src/main.py:C\n",
        "src/utils.py:C\n",
        "!!end\n",
        "Text after the block\n",
    ]

    for chunk in chunks:
        yield chunk
        await asyncio.sleep(0.1)  # Simulate streaming delay


# --8<-- [end:stream]


# --8<-- [start:main]
async def main() -> None:
    """Run the example."""
    print("=" * 60)
    print("Example 01: Plain Text Stream (Default Behavior)")
    print("=" * 60)
    print()

    # --8<-- [start:example]
    # Setup
    registry = Registry()
    registry.register("files_operations", FileOperations)
    processor = StreamBlockProcessor(registry)

    # Process stream
    print("Processing plain text stream...")
    print()

    async for event in processor.process_stream(plain_text_stream()):
        # Text deltas - emitted in real-time
        if isinstance(event, TextDeltaEvent):
            print(f"📝 Text Delta: {repr(event.delta)[:50]}", flush=True)

        # Raw text outside blocks
        elif isinstance(event, TextContentEvent):
            print(f"💬 Raw Text: {event.content}")

        # Extracted blocks
        elif isinstance(event, BlockEndEvent):
            block = event.get_block()
            if block is None:
                continue
            print("\n✅ Block Extracted:")
            print(block.model_dump_json(indent=2))
            print()
    # --8<-- [end:example]

    print()
    print("✓ Plain text streams work automatically!")
    print("✓ No adapter configuration needed")


# --8<-- [end:main]


if __name__ == "__main__":
    asyncio.run(main())
