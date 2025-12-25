#!/usr/bin/env python3
"""Define and use a custom block type."""

# --8<-- [start:imports]
import asyncio

from pydantic import Field
from streamblocks_examples.helpers.simulator import simple_text_stream

from hother.streamblocks import DelimiterFrontmatterSyntax, Registry, StreamBlockProcessor
from hother.streamblocks.core.models import Block
from hother.streamblocks.core.types import BaseContent, BaseMetadata, BlockEndEvent

# --8<-- [end:imports]


# --8<-- [start:models]
class TaskMetadata(BaseMetadata):
    """Custom metadata for task blocks."""

    id: str
    block_type: str
    title: str = "Untitled"
    priority: str = "normal"


class TaskContent(BaseContent):
    """Custom content for task blocks."""

    description: str = ""

    @classmethod
    def parse(cls, raw_text: str) -> "TaskContent":
        return cls(raw_content=raw_text, description=raw_text.strip())


TaskBlock = Block[TaskMetadata, TaskContent]
# --8<-- [end:models]


# --8<-- [start:main]
async def main() -> None:
    """Use a custom block type."""
    # --8<-- [start:example]
    syntax = DelimiterFrontmatterSyntax()
    registry = Registry(syntax=syntax)
    registry.register("task", TaskBlock)
    processor = StreamBlockProcessor(registry)

    text = "!!start\n---\nid: task-1\nblock_type: task\ntitle: Fix bug\npriority: high\n---\nFix the login issue\n!!end"

    async for event in processor.process_stream(simple_text_stream(text)):
        if isinstance(event, BlockEndEvent):
            block = event.get_block()
            if block and isinstance(block.metadata, TaskMetadata):
                print(f"Task: {block.metadata.title} ({block.metadata.priority})")
                if isinstance(block.content, TaskContent):
                    print(f"  Description: {block.content.description}")
    # --8<-- [end:example]


# --8<-- [end:main]


if __name__ == "__main__":
    asyncio.run(main())
