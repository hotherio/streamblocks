#!/usr/bin/env python3
"""Visualization block for charts, diagrams, and tables."""

# --8<-- [start:imports]
import asyncio
from textwrap import dedent

from hother.streamblocks import DelimiterFrontmatterSyntax, Registry, StreamBlockProcessor
from hother.streamblocks.core.types import BlockEndEvent
from hother.streamblocks_examples.blocks.agent.visualization import Visualization

# --8<-- [end:imports]


# --8<-- [start:main]
async def main() -> None:
    """Extract visualization blocks with chart and table data."""
    syntax = DelimiterFrontmatterSyntax()
    registry = Registry(syntax=syntax)
    registry.register("visualization", Visualization)
    processor = StreamBlockProcessor(registry)

    # --8<-- [start:stream]
    text = dedent("""
        !!start
        ---
        id: viz01
        block_type: visualization
        viz_type: chart
        title: Quarterly Sales
        format: markdown
        ---
        type: bar
        labels: [Q1, Q2, Q3, Q4]
        values: [100, 150, 120, 180]
        options:
          color: blue
        !!end

        !!start
        ---
        id: viz02
        block_type: visualization
        viz_type: table
        title: User Stats
        format: ascii
        ---
        headers: [Name, Score, Level]
        rows:
          - [Alice, 950, Expert]
          - [Bob, 720, Intermediate]
        !!end
    """).strip()

    from hother.streamblocks_examples.helpers.simulator import simple_text_stream

    # --8<-- [end:stream]

    # --8<-- [start:process]
    async for event in processor.process_stream(simple_text_stream(text)):
        if isinstance(event, BlockEndEvent):
            block = event.get_block()
            if block:
                print("Extracted visualization block:")
                print(block.model_dump_json(indent=2))
    # --8<-- [end:process]


# --8<-- [end:main]


if __name__ == "__main__":
    asyncio.run(main())
