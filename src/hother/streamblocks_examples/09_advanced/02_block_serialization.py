#!/usr/bin/env python3
"""Block serialization and persistence patterns."""

# --8<-- [start:imports]
import asyncio
import json
from textwrap import dedent

from hother.streamblocks import DelimiterFrontmatterSyntax, Registry, StreamBlockProcessor
from hother.streamblocks.core.types import BlockEndEvent
from hother.streamblocks_examples.blocks.agent.files import FileOperations

# --8<-- [end:imports]


# --8<-- [start:main]
async def main() -> None:
    """Demonstrate block serialization and restoration."""
    syntax = DelimiterFrontmatterSyntax()
    registry = Registry(syntax=syntax)
    registry.register("files_operations", FileOperations)
    processor = StreamBlockProcessor(registry)

    # --8<-- [start:extract]
    text = dedent("""
        !!start
        ---
        id: ops001
        block_type: files_operations
        description: Create project files
        ---
        src/main.py:C
        src/utils.py:E
        !!end
    """).strip()

    async def stream():
        yield text

    # Extract blocks
    blocks = []
    async for event in processor.process_stream(stream()):
        if isinstance(event, BlockEndEvent):
            block = event.get_block()
            if block:
                blocks.append(block)

    print(f"Extracted {len(blocks)} block(s)\n")
    # --8<-- [end:extract]

    # --8<-- [start:serialize]
    # Serialize block to JSON
    for block in blocks:
        # Use model_dump_json() for Pydantic serialization
        json_str = block.model_dump_json(indent=2)

        # Pretty print
        print("=== Serialized Block ===")
        print(json_str[:500] + "..." if len(json_str) > 500 else json_str)
        print()

        # Save to file (demonstration)
        # with open("block.json", "w") as f:
        #     json.dump(block_dict, f, indent=2)
    # --8<-- [end:serialize]

    # --8<-- [start:restore]
    # Restore from JSON
    print("=== Restoration ===")
    for block in blocks:
        # Serialize
        block_dict = block.model_dump(mode="json")
        json_str = json.dumps(block_dict)

        # Restore
        restored_dict = json.loads(json_str)

        # Access key fields
        print(f"Block ID: {restored_dict['metadata']['id']}")
        print(f"Block Type: {restored_dict['metadata']['block_type']}")
        print(f"Operations: {len(restored_dict['content']['operations'])}")

        # Validate restoration
        if restored_dict["metadata"]["id"] == block.metadata.id:
            print("Restoration verified!")
    # --8<-- [end:restore]


# --8<-- [end:main]


if __name__ == "__main__":
    asyncio.run(main())
