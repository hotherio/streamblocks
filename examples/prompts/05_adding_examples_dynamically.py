#!/usr/bin/env python3
"""Example demonstrating dynamic example management for blocks.

This example shows how to add examples programmatically at runtime using:
- add_example() - Add single example (dict or instance)
- add_examples() - Add multiple examples
- add_example_from_syntax() - Parse and add from syntax text
- clear_examples() - Remove dynamic examples
- get_examples() - Retrieve all examples (static + dynamic)
"""

from typing import Literal

from pydantic import BaseModel, Field

from hother.streamblocks import DelimiterPreambleSyntax, Syntax
from hother.streamblocks.blocks.files import FileOperations
from hother.streamblocks.blocks.structured_output import create_structured_output_block
from hother.streamblocks.core.models import Block
from hother.streamblocks.core.types import BaseContent, BaseMetadata

# ============================================================================
# Define Custom Block for Examples
# ============================================================================


class NoteMetadata(BaseMetadata):
    """Metadata for note blocks."""

    block_type: Literal["note"] = "note"  # type: ignore[assignment]
    tags: list[str] = Field(default_factory=list, description="Note tags")


class NoteContent(BaseContent):
    """Content for note blocks."""

    text: str = Field(description="Note text content")

    @classmethod
    def parse(cls, raw_text: str) -> "NoteContent":
        """Parse note content from raw text."""
        return cls(raw_content=raw_text, text=raw_text.strip())


class Note(Block[NoteMetadata, NoteContent]):
    """Simple note block for demonstrations."""

    __examples__ = [
        {
            "metadata": {"id": "n1", "block_type": "note", "tags": ["static"]},
            "content": {"text": "This is a static example from __examples__"},
        },
    ]


# ============================================================================
# Example 1: Add Example from Dictionary
# ============================================================================


def example_1_add_dict() -> None:
    """Demonstrate adding examples from dictionaries."""
    print("\n" + "=" * 80)
    print("EXAMPLE 1: Adding Examples from Dictionaries")
    print("=" * 80)

    # Clear any previous dynamic examples
    Note.clear_examples()

    print("\nInitial examples (only static __examples__):")
    print(f"  Count: {len(Note.get_examples())}")
    for ex in Note.get_examples():
        print(f"  - {ex.metadata.id}: {ex.content.text}")

    # Add example as dictionary
    print("\nAdding example from dictionary...")
    Note.add_example(
        {
            "metadata": {"id": "n2", "block_type": "note", "tags": ["dynamic", "dict"]},
            "content": {"text": "This example was added dynamically from a dict!"},
        }
    )

    print("\nAfter adding dynamic example:")
    print(f"  Count: {len(Note.get_examples())}")
    for ex in Note.get_examples():
        print(f"  - {ex.metadata.id}: {ex.content.text} [tags: {ex.metadata.tags}]")


# ============================================================================
# Example 2: Add Example from Instance
# ============================================================================


def example_2_add_instance() -> None:
    """Demonstrate adding examples from Block instances."""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Adding Examples from Instances")
    print("=" * 80)

    # Create a Note instance
    note_instance = Note(
        metadata=NoteMetadata(id="n3", block_type="note", tags=["dynamic", "instance"]),
        content=NoteContent(raw_content="Instance example", text="This example was created as an instance first!"),
    )

    print("\nCreated instance:")
    print(f"  ID: {note_instance.metadata.id}")
    print(f"  Text: {note_instance.content.text}")
    print(f"  Tags: {note_instance.metadata.tags}")

    # Add the instance
    print("\nAdding instance to examples...")
    Note.add_example(note_instance)

    print(f"\nTotal examples now: {len(Note.get_examples())}")
    for ex in Note.get_examples():
        print(f"  - {ex.metadata.id}: {ex.content.text[:50]}...")


# ============================================================================
# Example 3: Add Multiple Examples at Once
# ============================================================================


def example_3_add_multiple() -> None:
    """Demonstrate adding multiple examples at once."""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Adding Multiple Examples")
    print("=" * 80)

    print(f"\nCurrent count: {len(Note.get_examples())}")

    # Add multiple examples as a list
    print("\nAdding 3 examples at once...")
    Note.add_examples(
        [
            {
                "metadata": {"id": "n4", "block_type": "note", "tags": ["batch"]},
                "content": {"text": "First batch example"},
            },
            {
                "metadata": {"id": "n5", "block_type": "note", "tags": ["batch"]},
                "content": {"text": "Second batch example"},
            },
            {
                "metadata": {"id": "n6", "block_type": "note", "tags": ["batch"]},
                "content": {"text": "Third batch example"},
            },
        ]
    )

    print(f"\nAfter batch add: {len(Note.get_examples())} examples")
    print("\nBatch examples:")
    for ex in Note.get_examples():
        if "batch" in ex.metadata.tags:
            print(f"  - {ex.metadata.id}: {ex.content.text}")


# ============================================================================
# Example 4: Add Example from Syntax String (KEY FEATURE)
# ============================================================================


def example_4_add_from_syntax() -> None:
    """Demonstrate adding examples by parsing syntax strings."""
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Adding Examples from Syntax Text (KEY FEATURE)")
    print("=" * 80)

    print("\nThis is the most powerful feature - parse actual syntax format into examples!")

    # Clear previous examples for cleaner demo
    Note.clear_examples()

    # Define syntax text in delimiter preamble format
    syntax_text_1 = """!!n7:note
This note was parsed from delimiter syntax!
You can copy-paste actual block text and add it as an example.
!!end"""

    print("\nSyntax text to parse:")
    print("-" * 40)
    print(syntax_text_1)
    print("-" * 40)

    print("\nParsing and adding as example...")
    Note.add_example_from_syntax(syntax_text_1, Syntax.DELIMITER_PREAMBLE)

    print("\nSuccessfully added! Let's verify:")
    parsed_example = Note.get_examples()[-1]
    print(f"  ID: {parsed_example.metadata.id}")
    print(f"  Type: {parsed_example.metadata.block_type}")
    print(f"  Content: {parsed_example.content.text[:60]}...")

    # Add another one
    syntax_text_2 = """!!n8:note
Multi-line content is fully supported.
This makes it easy to add real-world examples.
Just copy the actual block format you want!
!!end"""

    print("\n\nAdding another example:")
    print("-" * 40)
    print(syntax_text_2)
    print("-" * 40)

    Note.add_example_from_syntax(syntax_text_2, Syntax.DELIMITER_PREAMBLE)

    print("\nBoth examples added from syntax:")
    print(f"  Total examples: {len(Note.get_examples())}")
    for ex in Note.get_examples():
        content_preview = " ".join(ex.content.text.split()[:5]) + "..."
        print(f"  - {ex.metadata.id}: {content_preview}")


# ============================================================================
# Example 5: FileOperations with Syntax Parsing
# ============================================================================


def example_5_file_operations_syntax() -> None:
    """Demonstrate parsing FileOperations from syntax."""
    print("\n" + "=" * 80)
    print("EXAMPLE 5: FileOperations from Syntax")
    print("=" * 80)

    print("\nFileOperations has its own custom format. Let's parse it!")

    # Clear previous dynamic examples
    FileOperations.clear_examples()

    file_ops_syntax = """!!f4:files_operations
src/new_feature.py:C
src/new_helper.py:C
tests/test_new_feature.py:C
!!end"""

    print("\nSyntax text:")
    print("-" * 40)
    print(file_ops_syntax)
    print("-" * 40)

    print("\nParsing and adding...")
    FileOperations.add_example_from_syntax(file_ops_syntax, Syntax.DELIMITER_PREAMBLE)

    print("\nParsed FileOperations example:")
    parsed = FileOperations.get_examples()[-1]
    print(f"  ID: {parsed.metadata.id}")
    print(f"  Operations ({len(parsed.content.operations)}):")
    for op in parsed.content.operations:
        print(f"    - {op.action}: {op.path}")


# ============================================================================
# Example 6: Structured Output Block with Dynamic Examples
# ============================================================================


def example_6_structured_output() -> None:
    """Demonstrate dynamic examples with structured output blocks."""
    print("\n" + "=" * 80)
    print("EXAMPLE 6: Structured Output Blocks")
    print("=" * 80)

    # Define a simple model
    class TodoItem(BaseModel):
        """Todo item model."""

        title: str = Field(description="Todo title")
        priority: str = Field(default="medium", description="Priority level")
        completed: bool = Field(default=False, description="Completion status")

    # Create structured block
    TodoBlock = create_structured_output_block(
        schema_model=TodoItem,
        schema_name="todo",
        format="json",
    )

    print("\nAdding todo examples dynamically...")

    # Add multiple examples as dictionaries
    print("\nAdding multiple todo examples...")
    TodoBlock.add_examples(
        [
            {
                "metadata": {"id": "t1", "block_type": "todo_block", "schema_name": "todo", "format": "json"},
                "content": {
                    "title": "Implement new feature",
                    "priority": "high",
                    "completed": False,
                },
            },
            {
                "metadata": {"id": "t2", "block_type": "todo_block", "schema_name": "todo", "format": "json"},
                "content": {
                    "title": "Write documentation",
                    "priority": "medium",
                    "completed": True,
                },
            },
        ]
    )

    print(f"\nTotal examples: {len(TodoBlock.get_examples())}")
    for ex in TodoBlock.get_examples():
        status = "✓" if ex.content.completed else "○"
        print(f"  {status} {ex.metadata.id}: {ex.content.title} [{ex.content.priority}]")


# ============================================================================
# Example 7: Static + Dynamic Examples Together
# ============================================================================


def example_7_static_and_dynamic() -> None:
    """Show how static and dynamic examples work together."""
    print("\n" + "=" * 80)
    print("EXAMPLE 7: Static + Dynamic Examples")
    print("=" * 80)

    # Note class has 1 static example in __examples__
    print("\nNote class has static examples in __examples__ attribute")

    # Clear dynamic to start fresh
    Note.clear_examples()

    print(f"\nAfter clear_examples(): {len(Note.get_examples())} example(s)")
    print("  (Static examples from __examples__ are NOT cleared)")

    for ex in Note.get_examples():
        print(f"  - {ex.metadata.id}: tags={ex.metadata.tags}")

    # Add dynamic examples
    print("\nAdding 2 dynamic examples...")
    Note.add_examples(
        [
            {
                "metadata": {"id": "n9", "block_type": "note", "tags": ["dynamic"]},
                "content": {"text": "Dynamic 1"},
            },
            {
                "metadata": {"id": "n10", "block_type": "note", "tags": ["dynamic"]},
                "content": {"text": "Dynamic 2"},
            },
        ]
    )

    print(f"\nTotal examples: {len(Note.get_examples())}")
    print("  Static examples (from __examples__):")
    for ex in Note.get_examples():
        if "static" in ex.metadata.tags:
            print(f"    - {ex.metadata.id}: {ex.content.text}")

    print("  Dynamic examples (from add_example):")
    for ex in Note.get_examples():
        if "dynamic" in ex.metadata.tags:
            print(f"    - {ex.metadata.id}: {ex.content.text}")


# ============================================================================
# Example 8: Error Handling
# ============================================================================


def example_8_error_handling() -> None:
    """Demonstrate error handling with invalid examples."""
    print("\n" + "=" * 80)
    print("EXAMPLE 8: Error Handling")
    print("=" * 80)

    print("\n1. Invalid dictionary (missing required field):")
    try:
        Note.add_example(
            {
                "metadata": {"id": "bad1", "block_type": "note"},
                # Missing 'content' field!
            }
        )
        print("  ERROR: Should have raised ValidationError!")
    except Exception as e:
        print(f"  ✓ Caught validation error: {type(e).__name__}")
        print(f"    {str(e)[:80]}...")

    print("\n2. Invalid syntax text (malformed):")
    try:
        bad_syntax = """!!bad2:note
This is missing the closing marker!"""
        Note.add_example_from_syntax(bad_syntax, Syntax.DELIMITER_PREAMBLE)
        print("  ERROR: Should have raised ValueError!")
    except ValueError as e:
        print(f"  ✓ Caught parsing error: {type(e).__name__}")
        print(f"    {e!s}")

    print("\n3. Invalid content for FileOperations:")
    try:
        FileOperations.add_example(
            {
                "metadata": {"id": "bad3", "block_type": "files_operations"},
                "content": {
                    "operations": [
                        {"action": "invalid_action", "path": "test.py"}  # Invalid action!
                    ],
                },
            }
        )
        print("  ERROR: Should have raised ValidationError!")
    except Exception as e:
        print(f"  ✓ Caught validation error: {type(e).__name__}")
        print(f"    {str(e)[:100]}...")

    print("\nAll error cases handled correctly!")


# ============================================================================
# Example 9: Using Dynamic Examples in Prompts
# ============================================================================


def example_9_dynamic_in_prompts() -> None:
    """Show how dynamic examples appear in generated prompts."""
    print("\n" + "=" * 80)
    print("EXAMPLE 9: Dynamic Examples in Generated Prompts")
    print("=" * 80)

    # Start fresh
    Note.clear_examples()

    print("\nGenerating prompt with only static examples...")
    prompt_before = Note.to_prompt(syntax=Syntax.DELIMITER_PREAMBLE, include_examples=True)
    examples_count_before = prompt_before.count("### Example")

    print(f"  Examples in prompt: {examples_count_before}")

    # Add dynamic examples
    print("\nAdding 2 dynamic examples...")
    Note.add_examples(
        [
            {
                "metadata": {"id": "p1", "block_type": "note"},
                "content": {"text": "Dynamic example for prompt 1"},
            },
            {
                "metadata": {"id": "p2", "block_type": "note"},
                "content": {"text": "Dynamic example for prompt 2"},
            },
        ]
    )

    print("\nGenerating prompt with static + dynamic examples...")
    prompt_after = Note.to_prompt(syntax=Syntax.DELIMITER_PREAMBLE, include_examples=True)
    examples_count_after = prompt_after.count("### Example")

    print(f"  Examples in prompt: {examples_count_after}")

    print("\nShowing examples section from prompt:")
    print("-" * 80)
    # Extract examples section
    if "## Examples" in prompt_after:
        examples_section = prompt_after.split("## Examples")[1]
        if "##" in examples_section:
            examples_section = examples_section.split("##")[0]
        print(examples_section[:500] + "...")
    print("-" * 80)


# ============================================================================
# Main
# ============================================================================


def main() -> None:
    """Run all examples."""
    print("=" * 80)
    print("📚 DYNAMIC EXAMPLE MANAGEMENT")
    print("Demonstrating programmatic example addition")
    print("=" * 80)

    example_1_add_dict()
    example_2_add_instance()
    example_3_add_multiple()
    example_4_add_from_syntax()  # KEY FEATURE
    example_5_file_operations_syntax()
    example_6_structured_output()
    example_7_static_and_dynamic()
    example_8_error_handling()
    example_9_dynamic_in_prompts()

    print("\n" + "=" * 80)
    print("✅ ALL EXAMPLES COMPLETED")
    print("=" * 80)
    print("\nKey Takeaways:")
    print("  • add_example() accepts both dicts and instances")
    print("  • add_examples() for batch operations")
    print("  • add_example_from_syntax() parses actual block format - MOST POWERFUL")
    print("  • clear_examples() only clears dynamic, not static __examples__")
    print("  • get_examples() returns both static and dynamic examples")
    print("  • All methods validate inputs and raise proper errors")
    print("\nWhen to Use:")
    print("  • Building examples programmatically at runtime")
    print("  • Loading examples from files or databases")
    print("  • Parsing real block outputs as examples")
    print("  • Testing with dynamically generated examples")
    print("  • Creating example libraries that can be extended")


if __name__ == "__main__":
    main()
