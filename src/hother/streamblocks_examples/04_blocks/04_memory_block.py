#!/usr/bin/env python3
"""Memory block for context storage and recall operations."""

# --8<-- [start:imports]
import asyncio
from textwrap import dedent

from hother.streamblocks import DelimiterFrontmatterSyntax, Registry, StreamBlockProcessor
from hother.streamblocks.core.types import BlockEndEvent
from hother.streamblocks_examples.blocks.agent.memory import Memory

# --8<-- [end:imports]


# --8<-- [start:main]
async def main() -> None:
    """Demonstrate memory operations: store, recall, update, delete, list."""
    syntax = DelimiterFrontmatterSyntax()
    registry = Registry(syntax=syntax)
    registry.register("memory", Memory)
    processor = StreamBlockProcessor(registry)

    # --8<-- [start:stream]
    text = dedent("""
        !!start
        ---
        id: mem01
        block_type: memory
        memory_type: store
        key: user_prefs
        namespace: session
        ttl_seconds: 3600
        ---
        value:
          theme: dark
          language: en
        !!end

        !!start
        ---
        id: mem02
        block_type: memory
        memory_type: recall
        key: user_prefs
        namespace: session
        ---
        !!end

        !!start
        ---
        id: mem03
        block_type: memory
        memory_type: list
        key: "*"
        namespace: session
        ---
        !!end
    """).strip()

    from hother.streamblocks_examples.helpers.simulator import simple_text_stream

    # --8<-- [end:stream]

    # --8<-- [start:process]
    async for event in processor.process_stream(simple_text_stream(text)):
        if isinstance(event, BlockEndEvent):
            block = event.get_block()
            if block:
                print("Extracted memory block:")
                print(block.model_dump_json(indent=2))
    # --8<-- [end:process]


# --8<-- [end:main]


if __name__ == "__main__":
    asyncio.run(main())
