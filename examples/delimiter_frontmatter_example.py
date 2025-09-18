"""Example demonstrating DelimiterFrontmatterSyntax with YAML frontmatter."""

import asyncio
from collections.abc import AsyncIterator

from pydantic import BaseModel

from streamblocks import (
    BlockRegistry,
    DelimiterFrontmatterSyntax,
    EventType,
    StreamBlockProcessor,
)


# Custom content models for this example
class TaskMetadata(BaseModel):
    """Metadata for task blocks."""

    id: str
    block_type: str
    priority: str = "medium"
    assignee: str | None = None
    due_date: str | None = None
    tags: list[str] = []


class TaskContent(BaseModel):
    """Content for task blocks."""

    description: str
    subtasks: list[str] = []

    @classmethod
    def parse(cls, raw_text: str) -> "TaskContent":
        """Parse task content from raw text."""
        lines = raw_text.strip().split("\n")
        if not lines:
            return cls(description="")

        description = lines[0]
        subtasks = []

        for line in lines[1:]:
            line = line.strip()
            if line.startswith("- ") or line.startswith("* "):
                subtasks.append(line[2:])

        return cls(description=description, subtasks=subtasks)

# Custom content model for projects
class ProjectMetadata(BaseModel):
    """Metadata for project blocks."""

    id: str
    block_type: str
    status: str = "planning"
    team: str | None = None
    start_date: str | None = None


class ProjectContent(BaseModel):
    """Content for project blocks."""

    text: str

    @classmethod
    def parse(cls, raw_text: str) -> "ProjectContent":
        """Parse project content."""
        return cls(text=raw_text.strip())


async def example_stream() -> AsyncIterator[str]:
    """Example stream with delimiter frontmatter blocks."""
    text = """
Let's manage some tasks using our custom delimiter syntax.

!!start
---
id: task-001
block_type: task
priority: high
assignee: alice
due_date: "2024-01-15"
tags: [backend, api, urgent]
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
---
Fix critical bug in payment processing
!!end

Now let's use a custom delimiter for project blocks:

##begin
---
id: proj-alpha
block_type: project
status: active
team: engineering
start_date: "2024-01-01"
---
Project Alpha: Next-gen platform
- Microservices architecture
- Real-time data processing
- ML-powered insights
##finish

That's all the tasks and projects!
"""

    # Chunk-based streaming with variable chunk sizes
    chunk_sizes = [40, 60, 50, 70, 45, 55, 65]
    i = 0
    chunk_idx = 0

    while i < len(text):
        chunk_size = chunk_sizes[chunk_idx % len(chunk_sizes)]
        chunk = text[i : i + chunk_size]
        yield chunk
        i += chunk_size
        chunk_idx += 1
        await asyncio.sleep(0.01)



async def main() -> None:
    """Main example function."""
    # Setup registry
    registry = BlockRegistry()

    # Register delimiter frontmatter syntaxes
    # 1. Standard !!start/!!end for tasks
    task_syntax = DelimiterFrontmatterSyntax(
        metadata_class=TaskMetadata,
        content_class=TaskContent,
        start_delimiter="!!start",
        end_delimiter="!!end",
    )
    registry.register_syntax(task_syntax, block_types=["task"], priority=1)

    # 2. Custom ##begin/##finish for projects
    project_syntax = DelimiterFrontmatterSyntax(
        metadata_class=ProjectMetadata,
        content_class=ProjectContent,
        start_delimiter="##begin",
        end_delimiter="##finish",
    )
    registry.register_syntax(project_syntax, block_types=["project"], priority=1)

    # Add validators
    def validate_task_priority(metadata: TaskMetadata, content: TaskContent) -> bool:
        """Ensure high priority tasks have assignees."""
        if metadata.priority == "high" and not metadata.assignee:
            return False
        return True

    def validate_project(metadata: ProjectMetadata, content: ProjectContent) -> bool:
        """Ensure active projects have teams."""
        if metadata.status == "active" and not metadata.team:
            return False
        return True

    registry.add_validator("task", validate_task_priority)
    registry.add_validator("project", validate_project)

    # Create processor
    processor = StreamBlockProcessor(registry, lines_buffer=8)

    # Process stream
    print("Processing delimiter frontmatter blocks...")
    print("-" * 70)

    blocks_extracted = []
    blocks_rejected = []

    async for event in processor.process_stream(example_stream()):
        if event.type == EventType.RAW_TEXT:
            # Raw text passed through
            if event.data.strip():
                print(f"[TEXT] {event.data.strip()}")

        elif event.type == EventType.BLOCK_DELTA:
            # Show section transitions
            section = event.metadata.get("section", "unknown")
            syntax = event.metadata["syntax"]

            # Only show meaningful updates
            if section == "metadata":
                if event.data.strip() == "---":
                    print(f"\n[DELTA] {syntax}: Entering metadata section")
            elif section == "content" and "---" in event.data:
                print(f"[DELTA] {syntax}: Entering content section")

        elif event.type == EventType.BLOCK_EXTRACTED:
            # Complete block extracted
            block = event.metadata["extracted_block"]
            blocks_extracted.append(block)

            print(f"\n[BLOCK] Extracted: {block.metadata.id}")
            print(f"        Type: {block.metadata.block_type}")
            print(f"        Syntax: {block.syntax_name}")

            if block.metadata.block_type == "task":
                print(f"        Priority: {block.metadata.priority}")
                print(f"        Assignee: {block.metadata.assignee or 'Unassigned'}")
                if block.metadata.due_date:
                    print(f"        Due: {block.metadata.due_date}")
                if block.metadata.tags:
                    print(f"        Tags: {', '.join(block.metadata.tags)}")
                print(f"        Description: {block.content.description}")
                if block.content.subtasks:
                    print(f"        Subtasks: {len(block.content.subtasks)}")

            elif block.metadata.block_type == "project":
                print(f"        Status: {block.metadata.status}")
                print(f"        Team: {block.metadata.team}")
                if block.metadata.start_date:
                    print(f"        Start: {block.metadata.start_date}")
                # Show first line of content
                first_line = block.content.text.split("\\n")[0]
                print(f"        Title: {first_line}")

        elif event.type == EventType.BLOCK_REJECTED:
            # Block rejected
            blocks_rejected.append(event)
            reason = event.metadata["reason"]
            syntax = event.metadata["syntax"]
            print(f"\n[REJECT] {syntax} block rejected: {reason}")
            lines = event.metadata.get("lines", ("?", "?"))
            print(f"         Lines: {lines[0]}-{lines[1]}")

    print("-" * 70)
    print(f"\nTotal blocks extracted: {len(blocks_extracted)}")
    print(f"Total blocks rejected: {len(blocks_rejected)}")

    # Show task summary
    tasks = [b for b in blocks_extracted if b.metadata.block_type == "task"]
    if tasks:
        print("\nTask Summary:")
        for task in tasks:
            status = "✓" if task.metadata.assignee else "⚠"
            print(f"  {status} {task.metadata.id}: {task.content.description[:50]}...")


if __name__ == "__main__":
    asyncio.run(main())
