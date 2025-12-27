"""Example demonstrating DelimiterFrontmatterSyntax with YAML frontmatter.

This example shows how to use the delimiter+frontmatter syntax.
"""

import asyncio
from textwrap import dedent

from pydantic import Field

from hother.streamblocks import DelimiterFrontmatterSyntax, Registry, StreamBlockProcessor
from hother.streamblocks.core.models import Block, ExtractedBlock
from hother.streamblocks.core.types import (
    BaseContent,
    BaseMetadata,
    BlockContentDeltaEvent,
    BlockEndEvent,
    BlockErrorEvent,
    BlockHeaderDeltaEvent,
    BlockMetadataDeltaEvent,
    TextContentEvent,
)
from hother.streamblocks_examples.helpers.simulator import simulated_stream


# Custom content models for this example
class TaskMetadata(BaseMetadata):
    """Metadata for task blocks."""

    id: str
    block_type: str
    title: str = "Untitled Task"
    priority: str = "medium"
    assignee: str | None = None
    due_date: str | None = None
    tags: list[str] = Field(default_factory=list[str])
    status: str = "todo"


class TaskContent(BaseContent):
    """Content for task blocks."""

    description: str = ""
    subtasks: list[str] = Field(default_factory=list[str])

    @classmethod
    def parse(cls, raw_text: str) -> "TaskContent":
        """Parse task content from raw text."""
        lines = raw_text.strip().split("\n")
        if not lines:
            return cls(raw_content=raw_text, description="")

        description = lines[0]
        subtasks: list[str] = []

        for line in lines[1:]:
            stripped = line.strip()
            if stripped.startswith(("- ", "* ")):
                subtasks.append(stripped[2:])

        return cls(raw_content=raw_text, description=description, subtasks=subtasks)


# Create the block type
TaskBlock = Block[TaskMetadata, TaskContent]


async def main() -> None:
    """Main example function."""
    print("=== DelimiterFrontmatterSyntax Example ===\n")

    # Create delimiter frontmatter syntax for tasks
    # Using standard !!start/!!end delimiters
    task_syntax = DelimiterFrontmatterSyntax(
        start_delimiter="!!start",
        end_delimiter="!!end",
    )

    # Create type-specific registry and register block
    registry = Registry(syntax=task_syntax)
    registry.register("task", TaskBlock)

    # Add validators
    def validate_task_priority(block: ExtractedBlock[TaskMetadata, TaskContent]) -> bool:
        """Ensure high priority tasks have assignees."""
        return not (block.metadata.priority in ["high", "urgent"] and not block.metadata.assignee)

    registry.add_validator("task", validate_task_priority)

    # Create processor with config
    from hother.streamblocks.core.processor import ProcessorConfig

    config = ProcessorConfig(lines_buffer=10)
    processor = StreamBlockProcessor(registry, config=config)

    # Example text with delimiter frontmatter blocks
    text = dedent("""
        Let's manage some tasks using delimiter+frontmatter syntax.

        !!start
        ---
        id: task-001
        block_type: task
        title: Implement authentication
        priority: high
        assignee: alice
        due_date: "2024-01-15"
        tags:
          - backend
          - api
          - urgent
        status: in_progress
        ---
        Implement user authentication API
        - Create JWT token generation
        - Add refresh token support
        - Implement password reset flow
        - Add 2FA support
        !!end

        Here's another task with simpler metadata:

        !!start
        ---
        id: task-002
        block_type: task
        title: Update documentation
        assignee: bob
        ---
        Update documentation
        - API reference docs
        - Installation guide
        - Contributing guidelines
        !!end

        And a minimal task:

        !!start
        ---
        id: task-003
        block_type: task
        title: Fix payment bug
        priority: urgent
        ---
        Fix critical bug in payment processing
        !!end

        Some text between blocks.

        !!start
        ---
        id: task-004
        block_type: task
        title: Performance optimization
        assignee: charlie
        tags:
          - performance
          - backend
        ---
        Optimize database queries
        - Add proper indexes
        - Implement query caching
        - Review N+1 queries
        !!end

        That's all for now!
    """)

    # Process stream
    print("Processing task blocks...\n")

    blocks_extracted: list[ExtractedBlock[BaseMetadata, BaseContent]] = []

    async for event in processor.process_stream(simulated_stream(text)):
        if isinstance(event, TextContentEvent):
            # Raw text passed through
            if event.content.strip():
                text = event.content.strip()
                if len(text) > 60:
                    text = text[:57] + "..."
                print(f"[TEXT] {text}")

        elif isinstance(event, (BlockHeaderDeltaEvent, BlockMetadataDeltaEvent, BlockContentDeltaEvent)):
            # Skip deltas for cleaner output
            pass

        elif isinstance(event, BlockEndEvent):
            # Complete block extracted
            block = event.get_block()
            if block is None:
                continue
            blocks_extracted.append(block)
            print("\n[TASK] Extracted:")
            print(block.model_dump_json(indent=2))

        elif isinstance(event, BlockErrorEvent):
            # Block rejected
            print(f"\n[REJECT] {event.reason}")

    print("\n\nEXTRACTED BLOCKS SUMMARY:")
    print(f"Total blocks: {len(blocks_extracted)}")
    print("\nExtracted blocks (full details):")
    for i, block in enumerate(blocks_extracted, 1):
        print(f"\n--- Block {i} ---")
        print(block.model_dump_json(indent=2))

    print("\n✓ DelimiterFrontmatterSyntax processing complete!")


if __name__ == "__main__":
    asyncio.run(main())
    asyncio.run(main())
