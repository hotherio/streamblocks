"""Example demonstrating all interactive block types."""

import asyncio
from collections.abc import AsyncIterator
from typing import Any

from hother.streamblocks import (
    DelimiterFrontmatterSyntax,
    EventType,
    Registry,
    StreamBlockProcessor,
)
from hother.streamblocks.blocks import (
    ChoiceContent,
    ChoiceMetadata,
    ConfirmContent,
    ConfirmMetadata,
    FormContent,
    FormMetadata,
    InputContent,
    InputMetadata,
    MultiChoiceContent,
    MultiChoiceMetadata,
    RankingContent,
    RankingMetadata,
    ScaleContent,
    ScaleMetadata,
    YesNoContent,
    YesNoMetadata,
)


async def example_stream() -> AsyncIterator[str]:
    """Example stream with all interactive block types."""
    text = """Welcome to the Interactive Blocks Demo!

Let's start with a simple yes/no question:

!!start
---
id: setup-continue
block_type: yesno
yes_label: "Continue Setup"
no_label: "Skip for Now"
---
prompt: "Would you like to configure your workspace settings now?"
!!end

Great! Now let's choose a theme:

!!start
---
id: theme-selection
block_type: choice
display_style: radio
required: true
---
prompt: "Select your preferred color theme:"
options:
  - "Light Mode"
  - "Dark Mode"
  - "High Contrast"
  - "Auto (Follow System)"
!!end

Let's enable some features:

!!start
---
id: feature-selection
block_type: multichoice
min_selections: 1
max_selections: 3
---
prompt: "Which optional features would you like to enable?"
options:
  - "Code completion"
  - "Syntax highlighting"
  - "Auto-save"
  - "Git integration"
  - "Terminal integration"
  - "Markdown preview"
!!end

Now, let's set up your project:

!!start
---
id: project-name
block_type: input
input_type: text
min_length: 3
max_length: 50
pattern: "^[a-zA-Z][a-zA-Z0-9-_]*$"
---
prompt: "Enter your project name:"
placeholder: "my-awesome-project"
default_value: ""
!!end

How's your experience so far?

!!start
---
id: experience-rating
block_type: scale
min_value: 1
max_value: 5
---
prompt: "How would you rate your experience so far?"
labels:
  1: "Poor"
  2: "Fair"
  3: "Good"
  4: "Very Good"
  5: "Excellent"
!!end

Let's prioritize some tasks:

!!start
---
id: priority-ranking
block_type: ranking
allow_partial: false
---
prompt: "Please rank these tasks by priority (drag to reorder):"
items:
  - "Fix critical bug in payment system"
  - "Add user profile feature"
  - "Update documentation"
  - "Optimize database queries"
  - "Implement dark mode"
!!end

Before we proceed, please confirm:

!!start
---
id: delete-confirm
block_type: confirm
confirm_label: "Yes, Delete"
cancel_label: "Keep It"
danger_mode: true
---
prompt: "Are you sure you want to delete the old configuration?"
message: |
  This action cannot be undone. The following will be deleted:
  - Previous theme settings
  - Old workspace configuration
  - Cached preferences
!!end

Finally, let's collect some user information:

!!start
---
id: user-registration
block_type: form
submit_label: "Create Account"
---
prompt: "Please fill out the registration form:"
fields:
  - name: username
    label: "Username"
    field_type: text
    required: true
    validation:
      min_length: 3

  - name: email
    label: "Email Address"
    field_type: email
    required: true

  - name: age
    label: "Age"
    field_type: number
    required: false
    validation:
      min: 13
      max: 120

  - name: newsletter
    label: "Subscribe to newsletter?"
    field_type: yesno
    required: false

  - name: country
    label: "Country"
    field_type: choice
    required: true
    options: ["USA", "Canada", "UK", "Other"]
!!end

That's all the interactive blocks! Thanks for trying the demo.
"""

    # Simulate chunk-based streaming
    chunk_size = 100
    for i in range(0, len(text), chunk_size):
        chunk = text[i : i + chunk_size]
        yield chunk
        await asyncio.sleep(0.01)


async def main() -> None:
    """Main example function."""
    # Note: The new design doesn't support dynamic type selection.
    # This example shows how to adapt by creating a custom syntax.
    print("⚠️  Note: This example uses a workaround for dynamic block types.")
    print("In the new design, each processor handles one syntax type.\n")

    # Create a block type to class mapping
    block_type_mapping = {
        "yesno": (YesNoMetadata, YesNoContent),
        "choice": (ChoiceMetadata, ChoiceContent),
        "multichoice": (MultiChoiceMetadata, MultiChoiceContent),
        "input": (InputMetadata, InputContent),
        "scale": (ScaleMetadata, ScaleContent),
        "ranking": (RankingMetadata, RankingContent),
        "confirm": (ConfirmMetadata, ConfirmContent),
        "form": (FormMetadata, FormContent),
    }

    # Create a custom syntax that can handle different block types
    class InteractiveSyntax(DelimiterFrontmatterSyntax):
        def __init__(self, block_mapping: dict[str, tuple[type, type]]) -> None:
            super().__init__(name="interactive_syntax")
            self.block_mapping = block_mapping

        def parse_block(self, candidate: Any) -> Any:
            # First, parse just the metadata to determine block type
            import yaml

            metadata_dict = {}
            if candidate.metadata_lines:
                yaml_content = "\n".join(candidate.metadata_lines)
                try:
                    metadata_dict = yaml.safe_load(yaml_content) or {}
                except Exception as e:
                    from hother.streamblocks.core.types import ParseResult

                    return ParseResult(success=False, error=f"Invalid YAML: {e}")

            # Get the block type
            block_type = metadata_dict.get("block_type", "unknown")

            # Set the appropriate classes
            if block_type in self.block_mapping:
                self.metadata_class, self.content_class = self.block_mapping[block_type]
            else:
                # Use base classes as fallback
                from hother.streamblocks.core.models import BaseContent, BaseMetadata

                self.metadata_class = BaseMetadata
                self.content_class = BaseContent

            # Now parse with the correct classes
            return super().parse_block(candidate)

    # Create a single syntax that can handle multiple block types
    # This is a workaround - normally you'd have separate processors
    interactive_syntax = InteractiveSyntax(block_mapping=block_type_mapping)

    # Create type-specific registry
    registry = Registry(interactive_syntax)

    # Create processor
    processor = StreamBlockProcessor(registry, lines_buffer=10)

    # Process stream
    print("🎯 Interactive Blocks Demo")
    print("=" * 70)

    blocks_extracted = []

    async for event in processor.process_stream(example_stream()):
        if event.type == EventType.RAW_TEXT:
            # Raw text passed through
            if event.data.strip():
                print(f"\n📝 {event.data.strip()}")

        elif event.type == EventType.BLOCK_EXTRACTED:
            # Complete block extracted
            block = event.content["extracted_block"]
            blocks_extracted.append(block)

            print(f"\n✅ Block Extracted: {block.definition.id}")
            print(f"   Type: {block.definition.block_type}")
            print(f"   Prompt: {block.definition.prompt}")

            # Show block-specific details
            if block.definition.block_type == "yesno":
                print(f"   Labels: [{block.definition.yes_label}] / [{block.definition.no_label}]")

            elif block.definition.block_type == "choice":
                print(f"   Style: {block.definition.display_style}")
                print(f"   Options: {len(block.definition.options)} choices")
                for i, opt in enumerate(block.definition.options, 1):
                    print(f"     {i}. {opt}")

            elif block.definition.block_type == "multichoice":
                print(f"   Selections: {block.definition.min_selections}-{block.definition.max_selections or 'all'}")
                print(f"   Options: {len(block.definition.options)} choices")

            elif block.definition.block_type == "input":
                print(f"   Type: {block.definition.input_type}")
                print(f"   Length: {block.definition.min_length}-{block.definition.max_length or 'unlimited'}")
                if block.definition.pattern:
                    print(f"   Pattern: {block.definition.pattern}")
                if block.definition.placeholder:
                    print(f"   Placeholder: {block.definition.placeholder}")

            elif block.definition.block_type == "scale":
                print(f"   Range: {block.definition.min_value}-{block.definition.max_value}")
                if block.definition.labels:
                    print(f"   Labels: {block.definition.labels}")

            elif block.definition.block_type == "ranking":
                print(f"   Items to rank: {len(block.definition.items)}")
                print(f"   Allow partial: {block.definition.allow_partial}")

            elif block.definition.block_type == "confirm":
                print(f"   Danger mode: {block.definition.danger_mode}")
                print(f"   Buttons: [{block.definition.confirm_label}] / [{block.definition.cancel_label}]")
                print(f"   Message preview: {block.definition.message[:50]}...")

            elif block.definition.block_type == "form":
                print(f"   Fields: {len(block.definition.fields)}")
                for field in block.definition.fields:
                    req = "required" if field.required else "optional"
                    print(f"     - {field.name} ({field.field_type}, {req})")

        elif event.type == EventType.BLOCK_REJECTED:
            # Block rejected
            print(f"\n❌ Block Rejected: {event.content['reason']}")
            print(f"   Syntax: {event.content['syntax']}")
            if "error" in event.content:
                print(f"   Error: {event.content['error']}")

    print("\n" + "=" * 70)
    print(f"📊 Total blocks extracted: {len(blocks_extracted)}")

    # Summary by type
    type_counts = {}
    for block in blocks_extracted:
        block_type = block.definition.block_type
        type_counts[block_type] = type_counts.get(block_type, 0) + 1

    print("\n📈 Blocks by type:")
    for block_type, count in sorted(type_counts.items()):
        print(f"   - {block_type}: {count}")


if __name__ == "__main__":
    asyncio.run(main())
