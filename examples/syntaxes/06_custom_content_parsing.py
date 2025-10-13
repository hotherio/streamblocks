"""Example demonstrating custom content parsing with parse() methods.

This advanced example shows WHEN and HOW to implement custom parse() methods
to extract structure from unstructured text content. Progressive examples
from simple to complex parsing patterns.
"""

import asyncio
from collections.abc import AsyncIterator
from typing import Literal

from pydantic import BaseModel, Field

import hother.streamblocks as sb
from hother.streamblocks.core.types import BaseContent, BaseMetadata


# =============================================================================
# Example A: Default Behavior (No Custom Parse)
# =============================================================================


class SimpleNoteMetadata(BaseMetadata):
    """Metadata for simple notes."""

    id: str
    block_type: Literal["simple_note"] = "simple_note"  # type: ignore[assignment]


class SimpleNoteContent(BaseContent):
    """Content using default parse() - just stores raw_content.

    Best for: Simple text blocks that don't need structure extraction.
    """

    # Uses inherited parse() method from BaseContent
    # Just stores content in raw_content field


SimpleNote = sb.Block[SimpleNoteMetadata, SimpleNoteContent]


# =============================================================================
# Example B: Simple Custom Parsing (Key-Value Pairs)
# =============================================================================


class ConfigMetadata(BaseMetadata):
    """Metadata for configuration blocks."""

    id: str
    block_type: Literal["config"] = "config"  # type: ignore[assignment]


class ConfigContent(BaseContent):
    """Content with simple key=value parsing.

    Best for: Configuration files, environment variables, simple settings.
    """

    settings: dict[str, str] = Field(default_factory=dict)

    @classmethod
    def parse(cls, raw_text: str) -> "ConfigContent":
        """Parse key=value pairs from raw text.

        Format: key=value (one per line)
        """
        settings = {}
        for line in raw_text.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):  # Skip empty lines and comments
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                settings[key.strip()] = value.strip()

        return cls(raw_content=raw_text, settings=settings)


ConfigBlock = sb.Block[ConfigMetadata, ConfigContent]


# =============================================================================
# Example C: Medium Complexity (Task with Subtasks)
# =============================================================================


class TaskMetadata(BaseMetadata):
    """Metadata for task blocks."""

    id: str
    block_type: Literal["task"] = "task"  # type: ignore[assignment]


class TaskContent(BaseContent):
    """Content with description + bullet list parsing.

    Best for: Tasks, checklists, structured notes with lists.
    """

    description: str = ""
    subtasks: list[str] = Field(default_factory=list)

    @classmethod
    def parse(cls, raw_text: str) -> "TaskContent":
        """Parse description (first line) + bullet list subtasks.

        Format:
            Description text
            - Subtask 1
            - Subtask 2
        """
        lines = raw_text.strip().split("\n")
        if not lines:
            return cls(raw_content=raw_text, description="", subtasks=[])

        # First line is description
        description = lines[0].strip()

        # Remaining lines starting with - or * are subtasks
        subtasks = []
        for line in lines[1:]:
            stripped = line.strip()
            if stripped.startswith(("- ", "* ")):
                subtasks.append(stripped[2:])

        return cls(raw_content=raw_text, description=description, subtasks=subtasks)


TaskBlock = sb.Block[TaskMetadata, TaskContent]


# =============================================================================
# Example D: Complex Parsing (File Operations)
# =============================================================================


class FileOperation(BaseModel):
    """Single file operation."""

    action: Literal["create", "edit", "delete"]
    path: str


class FileOpsMetadata(BaseMetadata):
    """Metadata for file operations."""

    id: str
    block_type: Literal["file_ops"] = "file_ops"  # type: ignore[assignment]


class FileOpsContent(BaseContent):
    """Content with structured file operations parsing.

    Best for: Domain-specific formats, structured data extraction.
    """

    operations: list[FileOperation] = Field(default_factory=list)

    @classmethod
    def parse(cls, raw_text: str) -> "FileOpsContent":
        """Parse file operations from path:action format.

        Format: path/to/file.py:C (C=create, E=edit, D=delete)
        """
        operations = []
        action_map = {"C": "create", "E": "edit", "D": "delete"}

        for line in raw_text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue

            if ":" not in line:
                # Invalid format - skip or raise error
                continue

            path, action_code = line.rsplit(":", 1)
            action_code = action_code.upper()

            if action_code in action_map:
                operations.append(
                    FileOperation(
                        action=action_map[action_code],  # type: ignore[arg-type]
                        path=path.strip(),
                    )
                )

        return cls(raw_content=raw_text, operations=operations)


FileOpsBlock = sb.Block[FileOpsMetadata, FileOpsContent]


# =============================================================================
# Example Stream with All Four Types
# =============================================================================


async def example_stream() -> AsyncIterator[str]:
    """Example stream demonstrating all four parsing approaches."""
    text = """
Let's demonstrate custom content parsing with progressive complexity.

# Example A: Simple note (no custom parsing)

!!a1:simple_note
This is a simple note block.
No custom parsing needed - content stored as-is in raw_content.
Perfect for plain text blocks!
!!end

# Example B: Configuration (simple key=value parsing)

!!b1:config
# Database configuration
host=localhost
port=5432
database=myapp_db
username=admin
max_connections=100
!!end

# Example C: Task with subtasks (medium complexity)

!!c1:task
Implement authentication system
- Add JWT token generation
- Create login endpoint
- Add password reset flow
- Implement 2FA support
!!end

# Example D: File operations (complex structured parsing)

!!d1:file_ops
src/auth.py:C
src/models.py:C
tests/test_auth.py:C
old_module.py:D
config.yaml:E
!!end

Now let's add one more of each to see the parsing in action:

!!a2:simple_note
Another simple note without any structure.
Just plain text stored in raw_content.
!!end

!!b2:config
# API settings
api_url=https://api.example.com
timeout=30
retry_count=3
!!end

!!c2:task
Code review checklist
- Check for code style violations
- Verify test coverage
- Review error handling
- Check documentation
!!end

!!d2:file_ops
README.md:E
docs/api.md:C
legacy/old.py:D
!!end

That's all for this demonstration!
"""

    # Simulate streaming
    chunk_size = 60
    for i in range(0, len(text), chunk_size):
        chunk = text[i : i + chunk_size]
        yield chunk
        await asyncio.sleep(0.005)


# =============================================================================
# Main Processing
# =============================================================================


async def main() -> None:
    """Main example function."""
    print("=" * 70)
    print("CUSTOM CONTENT PARSING EXAMPLES")
    print("=" * 70)
    print("\nProgression from simple to complex parse() implementations:\n")
    print("A. Default parsing (raw_content only)")
    print("B. Simple parsing (key=value pairs)")
    print("C. Medium parsing (description + bullet list)")
    print("D. Complex parsing (structured format conversion)")
    print()

    # Create registry and register all block types
    registry = sb.Registry(syntax=sb.DelimiterPreambleSyntax())
    registry.register("simple_note", SimpleNote)
    registry.register("config", ConfigBlock)
    registry.register("task", TaskBlock)
    registry.register("file_ops", FileOpsBlock)

    # Create processor
    processor = sb.StreamBlockProcessor(registry)

    # Process stream
    print("Processing blocks...\n")

    blocks_by_type: dict[str, list] = {
        "simple_note": [],
        "config": [],
        "task": [],
        "file_ops": [],
    }

    async for event in processor.process_stream(example_stream()):
        if event.type == sb.EventType.RAW_TEXT:
            # Show section headers
            if event.data.strip().startswith("# Example"):
                print(f"\n{event.data.strip()}")

        elif event.type == sb.EventType.BLOCK_EXTRACTED:
            block = event.block
            block_type = block.metadata.block_type

            if block_type in blocks_by_type:
                blocks_by_type[block_type].append(block)

                # Show what was extracted
                print(f"\n[{block_type.upper()}] {block.metadata.id} extracted")

                # Show parsing results based on type
                if block_type == "simple_note":
                    print(f"  Raw content: {block.content.raw_content[:50]}...")

                elif block_type == "config" and hasattr(block.content, "settings"):
                    print(f"  Settings extracted: {len(block.content.settings)} key-value pairs")
                    for key, value in list(block.content.settings.items())[:3]:
                        print(f"    {key} = {value}")

                elif block_type == "task" and hasattr(block.content, "subtasks"):
                    print(f"  Description: {block.content.description}")
                    print(f"  Subtasks: {len(block.content.subtasks)}")
                    for subtask in block.content.subtasks[:2]:
                        print(f"    - {subtask}")

                elif block_type == "file_ops" and hasattr(block.content, "operations"):
                    print(f"  Operations: {len(block.content.operations)}")
                    for op in block.content.operations[:3]:
                        print(f"    {op.action.upper()}: {op.path}")

    # Summary
    print("\n" + "=" * 70)
    print("PARSING SUMMARY")
    print("=" * 70)

    for block_type, blocks in blocks_by_type.items():
        print(f"\n{block_type.upper()}: {len(blocks)} blocks")

    # Guidelines
    print("\n" + "=" * 70)
    print("WHEN TO USE EACH APPROACH")
    print("=" * 70)

    print("\n📝 DEFAULT PARSE (raw_content only):")
    print("  ✓ Simple text blocks")
    print("  ✓ Already structured data (use metadata instead)")
    print("  ✓ Content used as-is without processing")
    print("  ✓ Code snippets, logs, documentation")

    print("\n📝 SIMPLE CUSTOM PARSE:")
    print("  ✓ Key-value pairs (config files, env vars)")
    print("  ✓ Simple format conversions")
    print("  ✓ Line-based structured data")
    print("  Example: ConfigContent (key=value parsing)")

    print("\n📝 MEDIUM CUSTOM PARSE:")
    print("  ✓ Mixed content with sections")
    print("  ✓ Description + list patterns")
    print("  ✓ Simple markdown-like formats")
    print("  Example: TaskContent (description + subtasks)")

    print("\n📝 COMPLEX CUSTOM PARSE:")
    print("  ✓ Domain-specific formats")
    print("  ✓ Structured data extraction")
    print("  ✓ Format transformations")
    print("  ✓ Validation during parsing")
    print("  Example: FileOpsContent (path:action → FileOperation)")

    print("\n" + "=" * 70)
    print("BEST PRACTICES")
    print("=" * 70)
    print("\n1. Always preserve raw_content:")
    print("   return cls(raw_content=raw_text, ...)")
    print("\n2. Handle edge cases:")
    print("   - Empty content")
    print("   - Malformed input")
    print("   - Missing expected patterns")
    print("\n3. Raise descriptive errors:")
    print("   - Validate format during parsing")
    print("   - Provide clear error messages")
    print("\n4. Keep parsing focused:")
    print("   - One responsibility per parse method")
    print("   - Don't mix parsing with business logic")
    print("\n5. Make it testable:")
    print("   - Pure function (no side effects)")
    print("   - Easy to unit test")

    print("\n✓ Custom content parsing examples complete!")


if __name__ == "__main__":
    asyncio.run(main())
