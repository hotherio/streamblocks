#!/usr/bin/env python3
"""Example demonstrating custom prompt strings for blocks.

This example shows how to provide a custom prompt directly as a multiline string
using the __prompt__ class attribute, bypassing the template generation system.
"""

from typing import Literal

from pydantic import BaseModel, Field

from hother.streamblocks import DelimiterPreambleSyntax, Registry, Syntax
from hother.streamblocks.blocks.structured_output import create_structured_output_block
from hother.streamblocks.core.models import Block
from hother.streamblocks.core.types import BaseContent, BaseMetadata

# ============================================================================
# Example 1: Simple Block with Custom Prompt
# ============================================================================


class SimpleTaskMetadata(BaseMetadata):
    """Metadata for simple task blocks."""

    block_type: Literal["simple_task"] = "simple_task"  # type: ignore[assignment]
    priority: str | None = Field(default=None, description="Task priority")


class SimpleTaskContent(BaseContent):
    """Content for simple task blocks."""

    task_description: str = Field(description="The task to be done")

    @classmethod
    def parse(cls, raw_text: str) -> "SimpleTaskContent":
        """Parse task from raw text."""
        return cls(raw_content=raw_text, task_description=raw_text.strip())


class SimpleTask(Block[SimpleTaskMetadata, SimpleTaskContent]):
    """Simple task block with custom prompt."""

    __prompt__ = """
# Simple Task Block

Output tasks using the delimiter format below. Each task should be concise and actionable.

## Format

```
!!<id>:simple_task
task description here
!!end
```

## Guidelines

1. Use clear, action-oriented language
2. Keep tasks concise (1-2 sentences)
3. Optionally specify priority in metadata

## Examples

```
!!t1:simple_task
Review pull request #123
!!end
```

```
!!t2:simple_task
Update documentation for new API endpoints
!!end
```
"""

    __examples__ = [
        {
            "metadata": {"id": "st1", "block_type": "simple_task"},
            "content": {"task_description": "Review pull request #123"},
        },
        {
            "metadata": {"id": "st2", "block_type": "simple_task", "priority": "high"},
            "content": {"task_description": "Fix critical bug in authentication"},
        },
    ]


# ============================================================================
# Example 2: Structured Output Block with Custom Prompt
# ============================================================================


class Decision(BaseModel):
    """Decision model."""

    question: str = Field(description="The decision question")
    options: list[str] = Field(description="Available options")
    chosen: str = Field(description="The chosen option")
    reasoning: str = Field(description="Explanation of the choice")


# Create the structured block
DecisionBlock = create_structured_output_block(
    schema_model=Decision,
    schema_name="decision",
    format="json",
)

# Override with custom prompt
DecisionBlock.__prompt__ = """
# Decision Block

Use this block when you need to make and document a decision.

## Format

```
!!<id>:decision_block
{
  "question": "What should we do?",
  "options": ["option1", "option2", "option3"],
  "chosen": "option2",
  "reasoning": "Because..."
}
!!end
```

## When to Use

- Making architectural decisions
- Choosing between implementation approaches
- Documenting trade-offs

## Example

```
!!d1:decision_block
{
  "question": "Which database should we use?",
  "options": ["PostgreSQL", "MongoDB", "MySQL"],
  "chosen": "PostgreSQL",
  "reasoning": "PostgreSQL provides ACID compliance, excellent JSON support, and mature ecosystem"
}
!!end
```
"""

DecisionBlock.__examples__ = [
    {
        "metadata": {"id": "d1", "block_type": "decision_block", "schema_name": "decision", "format": "json"},
        "content": {
            "question": "Which database should we use?",
            "options": ["PostgreSQL", "MongoDB", "MySQL"],
            "chosen": "PostgreSQL",
            "reasoning": "PostgreSQL provides ACID compliance and excellent JSON support",
        },
    },
]


# ============================================================================
# Main Examples
# ============================================================================


def example_1_custom_prompt_simple() -> None:
    """Show a simple block with custom prompt."""
    print("\n" + "=" * 80)
    print("EXAMPLE 1: Simple Block with Custom Prompt")
    print("=" * 80)

    # Get the custom prompt
    prompt = SimpleTask.to_prompt()

    print("\n" + prompt)
    print("\n" + "-" * 80)
    print("Note: This prompt was defined directly as a __prompt__ string,")
    print("not generated from templates!")


def example_2_custom_prompt_structured() -> None:
    """Show a structured block with custom prompt."""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Structured Block with Custom Prompt")
    print("=" * 80)

    # Get the custom prompt
    prompt = DecisionBlock.to_prompt()

    print("\n" + prompt)
    print("\n" + "-" * 80)
    print("Note: Even though this is a structured output block,")
    print("the custom __prompt__ overrides template generation!")


def example_3_registry_with_custom() -> None:
    """Show how custom prompts work in a registry."""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Registry with Custom Prompt Blocks")
    print("=" * 80)

    # Create registry
    syntax = DelimiterPreambleSyntax()
    registry = Registry(syntax=syntax)

    # Register blocks with custom prompts
    registry.register("simple_task", SimpleTask)
    registry.register("decision", DecisionBlock)

    # Generate registry prompt
    # Note: Currently this uses template generation for registry,
    # but individual block prompts use custom strings
    prompt = registry.to_prompt(include_examples=True)

    print("\n" + prompt)
    print("\n" + "-" * 80)
    print("Note: In a registry, blocks with __prompt__ will use")
    print("their custom prompts when rendered!")


def example_4_comparison() -> None:
    """Compare auto-generated vs custom prompts."""
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Comparison - Auto-Generated vs Custom")
    print("=" * 80)

    # Create a structured block WITHOUT custom prompt
    class SimpleModel(BaseModel):
        """Simple model for comparison."""

        name: str = Field(description="Name field")
        value: int = Field(description="Value field")

    AutoBlock = create_structured_output_block(
        schema_model=SimpleModel,
        schema_name="auto",
        format="json",
    )

    print("\n" + "-" * 80)
    print("AUTO-GENERATED PROMPT (template-based):")
    print("-" * 80)
    auto_prompt = AutoBlock.to_prompt(syntax=Syntax.DELIMITER_PREAMBLE)
    print(auto_prompt[:500] + "...")  # Show first 500 chars

    print("\n" + "-" * 80)
    print("CUSTOM PROMPT (__prompt__ attribute):")
    print("-" * 80)
    print(SimpleTask.__prompt__)

    print("\n" + "-" * 80)
    print("Key Differences:")
    print("  • Auto-generated: Comprehensive, schema-driven, consistent format")
    print("  • Custom: Concise, focused on specific use case, full control")


# ============================================================================
# Main
# ============================================================================


def main() -> None:
    """Run all examples."""
    print("=" * 80)
    print("📝 CUSTOM PROMPT STRINGS")
    print("Demonstrating __prompt__ attribute for custom prompts")
    print("=" * 80)

    example_1_custom_prompt_simple()
    example_2_custom_prompt_structured()
    example_3_registry_with_custom()
    example_4_comparison()

    print("\n" + "=" * 80)
    print("✅ ALL EXAMPLES COMPLETED")
    print("=" * 80)
    print("\nKey Takeaways:")
    print("  • Use __prompt__ for complete control over prompt generation")
    print("  • Custom prompts are multiline strings defined as class attributes")
    print("  • Works with any block type (custom or structured)")
    print("  • Bypasses template system entirely")
    print("\nWhen to Use:")
    print("  • You need specific instructions or tone")
    print("  • Template generation is too verbose")
    print("  • You want to optimize prompt tokens")
    print("  • You have domain-specific requirements")


if __name__ == "__main__":
    main()
