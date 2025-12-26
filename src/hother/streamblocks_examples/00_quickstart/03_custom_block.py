#!/usr/bin/env python3
"""Define and use a custom block type."""

# --8<-- [start:imports]
import asyncio

from hother.streamblocks import Registry, StreamBlockProcessor
from hother.streamblocks.core.models import Block
from hother.streamblocks.core.types import BaseContent, BaseMetadata, BlockEndEvent
from hother.streamblocks_examples.helpers.simulator import simple_text_stream

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
    registry = Registry()
    registry.register("task", TaskBlock)
    processor = StreamBlockProcessor(registry)

    text = "!!start\n---\nid: task-1\nblock_type: task\ntitle: Fix bug\npriority: high\n---\nFix the login issue\n!!end"
    stream = simple_text_stream(text)

    async for event in processor.process_stream(stream):
        if isinstance(event, BlockEndEvent):
            block = event.get_block()
            if block:
                print("\nExtracted Task Block:")
                print(block.model_dump_json(indent=2))
    # --8<-- [end:example]


# --8<-- [end:main]


if __name__ == "__main__":
    asyncio.run(main())
