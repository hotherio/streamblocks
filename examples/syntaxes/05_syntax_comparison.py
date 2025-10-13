"""Example comparing all three built-in syntax formats.

This example shows the SAME task data formatted in all three syntaxes,
helping you choose the right one for your use case.
"""

import asyncio
from collections.abc import AsyncIterator
from typing import Literal

from pydantic import Field

import hother.streamblocks as sb
from hother.streamblocks.core.models import Block
from hother.streamblocks.core.types import BaseContent, BaseMetadata


# =============================================================================
# Define a Simple Task Block
# =============================================================================


class TaskMetadata(BaseMetadata):
    """Metadata for task blocks."""

    id: str
    block_type: Literal["task"] = "task"  # type: ignore[assignment]
    priority: str = "medium"
    assignee: str | None = None


class TaskContent(BaseContent):
    """Content for task blocks."""

    description: str = ""
    subtasks: list[str] = Field(default_factory=list)

    @classmethod
    def parse(cls, raw_text: str) -> "TaskContent":
        """Parse task content."""
        lines = raw_text.strip().split("\n")
        if not lines:
            return cls(raw_content=raw_text)

        description = lines[0]
        subtasks = [line.strip()[2:] for line in lines[1:] if line.strip().startswith("- ")]

        return cls(raw_content=raw_text, description=description, subtasks=subtasks)


TaskBlock = Block[TaskMetadata, TaskContent]


# =============================================================================
# Stream Generators - Same Data in Different Syntaxes
# =============================================================================


async def delimiter_preamble_stream() -> AsyncIterator[str]:
    """Task in DelimiterPreambleSyntax format."""
    text = """
SYNTAX 1: DelimiterPreambleSyntax (Inline Metadata)

!!task01:task:high:alice
Implement authentication system
- Add JWT token generation
- Add refresh token support
- Implement password reset
!!end

Format: !!<id>:<type>[:<param1>:<param2>...]
"""
    for char in text:
        yield char
        await asyncio.sleep(0.001)


async def delimiter_frontmatter_stream() -> AsyncIterator[str]:
    """Task in DelimiterFrontmatterSyntax format."""
    text = """
SYNTAX 2: DelimiterFrontmatterSyntax (YAML Frontmatter)

!!start
---
id: task01
block_type: task
priority: high
assignee: alice
---
Implement authentication system
- Add JWT token generation
- Add refresh token support
- Implement password reset
!!end

Format: !!start ... YAML frontmatter ... content ... !!end
"""
    for char in text:
        yield char
        await asyncio.sleep(0.001)


async def markdown_frontmatter_stream() -> AsyncIterator[str]:
    """Task in MarkdownFrontmatterSyntax format."""
    text = """
SYNTAX 3: MarkdownFrontmatterSyntax (Markdown Code Blocks)

```task
---
id: task01
block_type: task
priority: high
assignee: alice
---
Implement authentication system
- Add JWT token generation
- Add refresh token support
- Implement password reset
```

Format: ```<type> ... YAML frontmatter ... content ... ```
"""
    for char in text:
        yield char
        await asyncio.sleep(0.001)


# =============================================================================
# Processing Functions
# =============================================================================


async def process_with_syntax(
    syntax, stream_gen: AsyncIterator[str], syntax_name: str
) -> None:
    """Process a stream with the given syntax."""
    print(f"\n{'=' * 70}")
    print(f"Processing with: {syntax_name}")
    print("=" * 70)

    registry = sb.Registry(syntax=syntax)
    registry.register("task", TaskBlock)
    processor = sb.StreamBlockProcessor(registry)

    async for event in processor.process_stream(stream_gen):
        if event.type == sb.EventType.RAW_TEXT:
            if event.data.strip() and not event.data.strip().startswith("Format:"):
                print(f"[TEXT] {event.data.strip()}")

        elif event.type == sb.EventType.BLOCK_EXTRACTED:
            block = event.block
            if isinstance(block.metadata, TaskMetadata) and isinstance(block.content, TaskContent):
                print(f"\n[EXTRACTED TASK]")
                print(f"  ID: {block.metadata.id}")
                print(f"  Priority: {block.metadata.priority}")
                print(f"  Assignee: {block.metadata.assignee}")
                print(f"  Description: {block.content.description}")
                if block.content.subtasks:
                    print(f"  Subtasks ({len(block.content.subtasks)}):")
                    for subtask in block.content.subtasks:
                        print(f"    - {subtask}")


# =============================================================================
# Main Comparison
# =============================================================================


async def main() -> None:
    """Compare all three syntaxes."""
    print("\n" + "=" * 70)
    print("STREAMBLOCKS SYNTAX COMPARISON")
    print("=" * 70)
    print("\nThis example shows the SAME task data in all three formats.")
    print("Choose the syntax that best fits your use case!\n")

    # 1. DelimiterPreambleSyntax
    syntax1 = sb.DelimiterPreambleSyntax()
    await process_with_syntax(syntax1, delimiter_preamble_stream(), "DelimiterPreambleSyntax")

    # 2. DelimiterFrontmatterSyntax
    syntax2 = sb.DelimiterFrontmatterSyntax()
    await process_with_syntax(syntax2, delimiter_frontmatter_stream(), "DelimiterFrontmatterSyntax")

    # 3. MarkdownFrontmatterSyntax
    syntax3 = sb.MarkdownFrontmatterSyntax(info_string="task")
    await process_with_syntax(syntax3, markdown_frontmatter_stream(), "MarkdownFrontmatterSyntax")

    # Summary
    print("\n" + "=" * 70)
    print("SYNTAX COMPARISON SUMMARY")
    print("=" * 70)

    print("\n1. DelimiterPreambleSyntax (!!id:type[:params])")
    print("   ✓ Most compact format")
    print("   ✓ Inline metadata (id, type, params)")
    print("   ✓ Best for simple use cases")
    print("   ✓ Minimal syntax overhead")
    print("   ✗ Limited metadata (only inline params)")
    print("   Use when: You have simple blocks with minimal metadata")

    print("\n2. DelimiterFrontmatterSyntax (!!start ... YAML ... !!end)")
    print("   ✓ Full YAML frontmatter support")
    print("   ✓ Rich metadata with nested structures")
    print("   ✓ Clear separation of metadata and content")
    print("   ✓ Human-readable")
    print("   ✗ More verbose than preamble")
    print("   Use when: You need rich metadata and prefer delimiter blocks")

    print("\n3. MarkdownFrontmatterSyntax (```type ... YAML ... ```)")
    print("   ✓ Full YAML frontmatter support")
    print("   ✓ Markdown-compatible (renders in editors)")
    print("   ✓ Syntax highlighting in most editors")
    print("   ✓ Familiar to developers")
    print("   ✗ Requires info_string configuration")
    print("   Use when: You're working with markdown documents")

    print("\n" + "=" * 70)
    print("CHOOSING THE RIGHT SYNTAX")
    print("=" * 70)
    print("\nSimple blocks, minimal metadata?")
    print("  → Use DelimiterPreambleSyntax")
    print("\nRich metadata, custom format?")
    print("  → Use DelimiterFrontmatterSyntax")
    print("\nMarkdown documents?")
    print("  → Use MarkdownFrontmatterSyntax")
    print("\nNeed to mix multiple syntaxes?")
    print("  → Create separate processors for each syntax")


if __name__ == "__main__":
    asyncio.run(main())
