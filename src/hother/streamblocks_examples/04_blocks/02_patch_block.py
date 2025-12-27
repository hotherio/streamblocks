#!/usr/bin/env python3
"""Patch block for code diffs and modifications."""

# --8<-- [start:imports]
import asyncio
from textwrap import dedent

from hother.streamblocks import DelimiterFrontmatterSyntax, Registry, StreamBlockProcessor
from hother.streamblocks.core.types import BlockEndEvent
from hother.streamblocks_examples.blocks.agent.patch import Patch

# --8<-- [end:imports]


# --8<-- [start:main]
async def main() -> None:
    """Extract patch blocks with diff content."""
    # --8<-- [start:setup]
    syntax = DelimiterFrontmatterSyntax()
    registry = Registry(syntax=syntax)
    registry.register("patch", Patch)
    processor = StreamBlockProcessor(registry)
    # --8<-- [end:setup]

    # --8<-- [start:stream]
    text = dedent("""
        !!start
        ---
        id: patch01
        block_type: patch
        file: src/utils.py
        start_line: 42
        author: developer
        description: Fix null check
        ---
        -if value is None:
        +if value is None or value == "":
             return default
        !!end
    """).strip()

    from hother.streamblocks_examples.helpers.simulator import simple_text_stream

    # --8<-- [end:stream]

    # --8<-- [start:process]
    async for event in processor.process_stream(simple_text_stream(text)):
        if isinstance(event, BlockEndEvent):
            block = event.get_block()
            if block:
                print("Extracted patch block:")
                print(block.model_dump_json(indent=2))
    # --8<-- [end:process]


# --8<-- [end:main]


if __name__ == "__main__":
    asyncio.run(main())
