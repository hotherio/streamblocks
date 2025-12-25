"""Example demonstrating DelimiterFrontmatterSyntax with YAML frontmatter.

This example shows how to use the delimiter+frontmatter syntax with the new
single-syntax design. Each processor handles one syntax type.
"""

import asyncio
from collections.abc import AsyncIterator
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


async def example_stream() -> AsyncIterator[str]:
    """Example stream with delimiter frontmatter blocks."""
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
    # Simulate streaming
    chunk_size = 50
    for i in range(0, len(text), chunk_size):
        chunk = text[i : i + chunk_size]
        yield chunk
        await asyncio.sleep(0.01)


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

    # Process stream
    print("Processing task blocks...\n")

    blocks_extracted: list[ExtractedBlock[BaseMetadata, BaseContent]] = []

    async for event in processor.process_stream(example_stream()):
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

            # Type narrow to TaskMetadata and TaskContent for specific access
            if isinstance(block.metadata, TaskMetadata) and isinstance(block.content, TaskContent):
                metadata = block.metadata
                content = block.content

                print(f"\n{'=' * 60}")
                print(f"[TASK] {metadata.id} - {metadata.title}")
                print(f"       Priority: {metadata.priority}")
                print(f"       Status: {metadata.status}")
                if metadata.assignee:
                    print(f"       Assignee: {metadata.assignee}")
                if metadata.due_date:
                    print(f"       Due: {metadata.due_date}")
                if metadata.tags:
                    print(f"       Tags: {', '.join(metadata.tags)}")

                print(f"\n       Description: {content.description}")
                if content.subtasks:
                    print("       Subtasks:")
                    for subtask in content.subtasks:
                        print(f"         - {subtask}")
                print("=" * 60)

        elif isinstance(event, BlockErrorEvent):
            # Block rejected
            print(f"\n[REJECT] {event.reason}")

    print("\n\nEXTRACTED BLOCKS SUMMARY:")
    print(f"Total blocks: {len(blocks_extracted)}")
    print("\nTasks:")
    for task in blocks_extracted:
        # Type narrow to TaskMetadata for specific access
        if isinstance(task.metadata, TaskMetadata):
            print(f"  - [{task.metadata.priority.upper()}] {task.metadata.title}")
            print(f"    Assignee: {task.metadata.assignee or 'Unassigned'}")
            print(f"    Status: {task.metadata.status}")

    print("\n✓ DelimiterFrontmatterSyntax processing complete!")


if __name__ == "__main__":
    asyncio.run(main())
    asyncio.run(main())
