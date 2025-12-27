#!/usr/bin/env python3
"""ToolCall block for invoking external tools with parameters."""

# --8<-- [start:imports]
import asyncio
from textwrap import dedent
from typing import Any

from hother.streamblocks import DelimiterFrontmatterSyntax, Registry, StreamBlockProcessor
from hother.streamblocks.core.types import BlockEndEvent
from hother.streamblocks_examples.blocks.agent.toolcall import ToolCall

# --8<-- [end:imports]


# --8<-- [start:tools]
def execute_tool(name: str, params: dict[str, Any]) -> str:
    """Mock tool execution."""
    if name == "search_web":
        return f"Results for: {params.get('query', '')}"
    if name == "get_weather":
        return f"Weather in {params.get('city', 'Unknown')}: Sunny, 22C"
    return f"Unknown tool: {name}"


# --8<-- [end:tools]


# --8<-- [start:main]
async def main() -> None:
    """Extract and execute tool call blocks."""
    syntax = DelimiterFrontmatterSyntax()
    registry = Registry(syntax=syntax)
    registry.register("tool_call", ToolCall)
    processor = StreamBlockProcessor(registry)

    # --8<-- [start:stream]
    text = dedent("""
        !!start
        ---
        id: tool01
        block_type: tool_call
        tool_name: search_web
        async_call: true
        timeout: 30.0
        ---
        query: "python async patterns"
        max_results: 5
        !!end
    """).strip()

    from hother.streamblocks_examples.helpers.simulator import simple_text_stream

    # --8<-- [end:stream]

    # --8<-- [start:process]
    async for event in processor.process_stream(simple_text_stream(text)):
        if isinstance(event, BlockEndEvent):
            block = event.get_block()
            if block:
                print("Extracted tool call block:")
                print(block.model_dump_json(indent=2))
                result = execute_tool(block.metadata.tool_name, block.content.parameters)
                print(f"Result: {result}")
    # --8<-- [end:process]


# --8<-- [end:main]


if __name__ == "__main__":
    asyncio.run(main())
