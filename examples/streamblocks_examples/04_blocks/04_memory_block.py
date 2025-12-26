#!/usr/bin/env python3
"""Memory block for context storage and recall operations."""

# --8<-- [start:imports]
import asyncio
from textwrap import dedent

from examples.blocks.agent.memory import Memory
from hother.streamblocks import DelimiterFrontmatterSyntax, Registry, StreamBlockProcessor
from hother.streamblocks.core.types import BlockEndEvent

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

    from streamblocks_examples.helpers.simulator import simple_text_stream

    # --8<-- [end:stream]

    # --8<-- [start:process]
    async for event in processor.process_stream(simple_text_stream(text)):
        if isinstance(event, BlockEndEvent):
            block = event.get_block()
            if block:
                op = block.metadata.memory_type
                key = block.metadata.key
                ns = block.metadata.namespace
                print(f"[{op.upper()}] key={key}, namespace={ns}")
                if block.content.value:
                    print(f"  Value: {block.content.value}")
                if block.metadata.ttl_seconds:
                    print(f"  TTL: {block.metadata.ttl_seconds}s")
    # --8<-- [end:process]


# --8<-- [end:main]


if __name__ == "__main__":
    asyncio.run(main())
