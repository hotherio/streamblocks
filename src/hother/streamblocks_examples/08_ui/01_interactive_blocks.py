"""Example demonstrating all interactive block types."""

import asyncio
from collections.abc import AsyncIterator
from textwrap import dedent
from typing import TYPE_CHECKING, Any

from hother.streamblocks import DelimiterFrontmatterSyntax, Registry, StreamBlockProcessor
from hother.streamblocks.core.types import BlockEndEvent, BlockErrorEvent, TextContentEvent
from hother.streamblocks_examples.blocks.agent.interactive import (
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

if TYPE_CHECKING:
    from hother.streamblocks.core.models import ExtractedBlock
    from hother.streamblocks.core.types import BaseContent, BaseMetadata


async def example_stream() -> AsyncIterator[str]:
    """Example stream with all interactive block types."""
    text = dedent("""
        Welcome to the Interactive Blocks Demo!

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
    """)

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
            super().__init__()
            self.block_mapping = block_mapping

        def parse_block(self, candidate: Any, block_class: type[Any] | None = None) -> Any:
            # First, parse just the metadata to determine block type
            import yaml

            from hother.streamblocks.core.models import Block
            from hother.streamblocks.core.types import ParseResult

            metadata_dict: dict[str, Any] = {}
            if candidate.metadata_lines:
                yaml_content = "\n".join(candidate.metadata_lines)
                try:
                    metadata_dict = yaml.safe_load(yaml_content)
                except Exception as e:
                    return ParseResult[Any, Any](success=False, error=f"Invalid YAML: {e}", exception=e)

            # Get the block type
            block_type: str = str(metadata_dict.get("block_type", "unknown"))

            # Determine the appropriate block class based on block_type
            if block_type in self.block_mapping:
                metadata_class, content_class = self.block_mapping[block_type]
                # Create a block class with these types
                dynamic_block_class = Block[metadata_class, content_class]
            else:
                # Use None to fall back to base classes
                dynamic_block_class = None

            # Now parse with the correct block class
            return super().parse_block(candidate, dynamic_block_class)

    # Create a single syntax that can handle multiple block types
    # This is a workaround - normally you'd have separate processors
    interactive_syntax = InteractiveSyntax(block_mapping=block_type_mapping)

    # Create type-specific registry
    registry = Registry(syntax=interactive_syntax)

    # Create processor with config
    from hother.streamblocks.core.processor import ProcessorConfig

    config = ProcessorConfig(lines_buffer=10)
    processor = StreamBlockProcessor(registry, config=config)

    # Process stream
    print("🎯 Interactive Blocks Demo")
    print("=" * 70)

    blocks_extracted: list[ExtractedBlock[BaseMetadata, BaseContent]] = []

    async for event in processor.process_stream(example_stream()):
        if isinstance(event, TextContentEvent):
            # Raw text passed through
            if event.content.strip():
                print(f"\n📝 {event.content.strip()}")

        elif isinstance(event, BlockEndEvent):
            # Complete block extracted
            block = event.get_block()
            if block is None:
                continue
            blocks_extracted.append(block)

            print(f"\n✅ Block Extracted: {block.metadata.id}")
            print(block.model_dump_json(indent=2))

        elif isinstance(event, BlockErrorEvent):
            # Block rejected
            print(f"\n❌ Block Rejected: {event.reason}")
            print(f"   Syntax: {event.syntax}")

    print("\n" + "=" * 70)
    print(f"📊 Total blocks extracted: {len(blocks_extracted)}")

    # Summary by type
    type_counts: dict[str, int] = {}
    for block in blocks_extracted:
        block_type = block.metadata.block_type
        type_counts[block_type] = type_counts.get(block_type, 0) + 1

    print("\n📈 Blocks by type:")
    for block_type, count in sorted(type_counts.items()):
        print(f"   - {block_type}: {count}")


if __name__ == "__main__":
    asyncio.run(main())
