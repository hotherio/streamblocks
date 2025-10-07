"""Tests for interactive blocks."""

import asyncio
from typing import Any

import pytest
import yaml

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
from hother.streamblocks.core.models import BaseContent, BaseMetadata
from hother.streamblocks.core.types import ParseResult

# Block type mapping for all interactive types
BLOCK_TYPE_MAPPING = {
    "yesno": (YesNoMetadata, YesNoContent),
    "choice": (ChoiceMetadata, ChoiceContent),
    "multichoice": (MultiChoiceMetadata, MultiChoiceContent),
    "input": (InputMetadata, InputContent),
    "scale": (ScaleMetadata, ScaleContent),
    "ranking": (RankingMetadata, RankingContent),
    "confirm": (ConfirmMetadata, ConfirmContent),
    "form": (FormMetadata, FormContent),
}


class InteractiveSyntax(DelimiterFrontmatterSyntax):
    """Test syntax that can handle all interactive block types."""

    def __init__(self) -> None:
        super().__init__(name="interactive", metadata_class=BaseMetadata, content_class=BaseContent)

    def parse_block(self, candidate: Any) -> ParseResult[Any, Any]:
        # Parse metadata to get block type
        metadata_dict = {}
        if candidate.metadata_lines:
            yaml_content = "\n".join(candidate.metadata_lines)
            try:
                metadata_dict = yaml.safe_load(yaml_content) or {}
            except Exception as e:
                return ParseResult(success=False, error=f"Invalid YAML: {e}")

        block_type = metadata_dict.get("block_type", "unknown")

        # Set the appropriate classes
        if block_type in BLOCK_TYPE_MAPPING:
            self.metadata_class, self.content_class = BLOCK_TYPE_MAPPING[block_type]
        else:
            return ParseResult(success=False, error=f"Unknown block type: {block_type}")

        # Parse with correct classes
        return super().parse_block(candidate)


@pytest.fixture
def interactive_registry() -> Registry:
    """Create a registry configured for interactive blocks."""
    syntax = InteractiveSyntax()
    return Registry(syntax)


@pytest.mark.asyncio
async def test_yesno_block(interactive_registry: Registry) -> None:
    """Test yes/no interactive block."""
    processor = StreamBlockProcessor(interactive_registry)

    async def mock_stream() -> Any:
        # Use the same format as the example - no indentation in content
        text = """!!start
---
id: test-yesno
block_type: yesno
yes_label: "Accept"
no_label: "Decline"
---
prompt: "Do you accept the terms?"
!!end
"""

        # Simulate chunk-based streaming like the example
        chunk_size = 50
        for i in range(0, len(text), chunk_size):
            chunk = text[i : i + chunk_size]
            yield chunk
            await asyncio.sleep(0.01)

    blocks = []
    rejected = []
    async for event in processor.process_stream(mock_stream()):
        if event.type == EventType.BLOCK_EXTRACTED:
            blocks.append(event.content["extracted_block"])
        elif event.type == EventType.BLOCK_REJECTED:
            rejected.append((event.content["reason"], event.content.get("error")))
    if rejected:
        print(f"Rejected: {rejected}")
    assert len(blocks) == 1
    block = blocks[0]

    assert block.definition.id == "test-yesno"
    assert block.definition.block_type == "yesno"
    assert block.definition.yes_label == "Accept"
    assert block.definition.no_label == "Decline"
    assert block.definition.prompt == "Do you accept the terms?"
    assert block.definition.response is None  # No response yet


@pytest.mark.asyncio
async def test_choice_block(interactive_registry: Registry) -> None:
    """Test single choice block."""
    processor = StreamBlockProcessor(interactive_registry)

    async def mock_stream() -> Any:
        text = """!!start
---
id: test-choice
block_type: choice
display_style: dropdown
---
prompt: "Select your favorite color:"
options:
  - "Red"
  - "Green"
  - "Blue"
!!end
"""

        # Simulate chunk-based streaming like the example
        chunk_size = 50
        for i in range(0, len(text), chunk_size):
            chunk = text[i : i + chunk_size]
            yield chunk
            await asyncio.sleep(0.01)

    blocks = []
    rejected = []
    async for event in processor.process_stream(mock_stream()):
        if event.type == EventType.BLOCK_EXTRACTED:
            blocks.append(event.content["extracted_block"])
        elif event.type == EventType.BLOCK_REJECTED:
            rejected.append((event.content["reason"], event.content.get("error")))

    if rejected:
        print(f"Rejected: {rejected}")
    assert len(blocks) == 1
    block = blocks[0]

    assert block.definition.display_style == "dropdown"
    assert block.definition.prompt == "Select your favorite color:"
    assert block.definition.options == ["Red", "Green", "Blue"]


@pytest.mark.asyncio
async def test_multichoice_block(interactive_registry: Registry) -> None:
    """Test multiple choice block."""
    processor = StreamBlockProcessor(interactive_registry)

    async def mock_stream() -> Any:
        text = """!!start
---
id: test-multi
block_type: multichoice
min_selections: 2
max_selections: 3
---
prompt: "Select your skills:"
options:
  - "Python"
  - "JavaScript"
  - "TypeScript"
  - "Rust"
  - "Go"
!!end
"""

        # Simulate chunk-based streaming like the example
        chunk_size = 50
        for i in range(0, len(text), chunk_size):
            chunk = text[i : i + chunk_size]
            yield chunk
            await asyncio.sleep(0.01)

    blocks = []
    rejected = []
    async for event in processor.process_stream(mock_stream()):
        if event.type == EventType.BLOCK_EXTRACTED:
            blocks.append(event.content["extracted_block"])
        elif event.type == EventType.BLOCK_REJECTED:
            rejected.append((event.content["reason"], event.content.get("error")))

    if rejected:
        print(f"Rejected: {rejected}")
    assert len(blocks) == 1
    block = blocks[0]

    assert block.definition.min_selections == 2
    assert block.definition.max_selections == 3
    assert len(block.definition.options) == 5
    assert block.definition.response == []  # Empty list by default


@pytest.mark.asyncio
async def test_scale_block(interactive_registry: Registry) -> None:
    """Test scale rating block."""
    processor = StreamBlockProcessor(interactive_registry)

    async def mock_stream() -> Any:
        text = """!!start
---
id: test-scale
block_type: scale
min_value: 0
max_value: 10
step: 2
---
prompt: "Rate your satisfaction:"
labels:
  0: "Very Poor"
  5: "Average"
  10: "Excellent"
!!end
"""

        # Simulate chunk-based streaming like the example
        chunk_size = 50
        for i in range(0, len(text), chunk_size):
            chunk = text[i : i + chunk_size]
            yield chunk
            await asyncio.sleep(0.01)

    blocks = []
    rejected = []
    async for event in processor.process_stream(mock_stream()):
        if event.type == EventType.BLOCK_EXTRACTED:
            blocks.append(event.content["extracted_block"])
        elif event.type == EventType.BLOCK_REJECTED:
            rejected.append((event.content["reason"], event.content.get("error")))

    if rejected:
        print(f"Rejected: {rejected}")
    assert len(blocks) == 1
    block = blocks[0]

    assert block.definition.min_value == 0
    assert block.definition.max_value == 10
    assert block.definition.step == 2
    assert block.definition.labels == {0: "Very Poor", 5: "Average", 10: "Excellent"}


@pytest.mark.asyncio
async def test_form_block(interactive_registry: Registry) -> None:
    """Test form block with multiple fields."""
    processor = StreamBlockProcessor(interactive_registry)

    async def mock_stream() -> Any:
        text = """!!start
---
id: test-form
block_type: form
submit_label: "Register"
cancel_label: "Skip"
---
prompt: "User Registration:"
fields:
  - name: username
    label: "Username"
    field_type: text
    required: true
    validation:
      min_length: 3
      max_length: 20

  - name: email
    label: "Email"
    field_type: email
    required: true

  - name: subscribe
    label: "Subscribe to newsletter?"
    field_type: yesno
    required: false
!!end
"""

        # Simulate chunk-based streaming like the example
        chunk_size = 50
        for i in range(0, len(text), chunk_size):
            chunk = text[i : i + chunk_size]
            yield chunk
            await asyncio.sleep(0.01)

    blocks = []
    rejected = []
    async for event in processor.process_stream(mock_stream()):
        if event.type == EventType.BLOCK_EXTRACTED:
            blocks.append(event.content["extracted_block"])
        elif event.type == EventType.BLOCK_REJECTED:
            rejected.append((event.content["reason"], event.content.get("error")))

    if rejected:
        print(f"Rejected: {rejected}")
    assert len(blocks) == 1
    block = blocks[0]

    assert block.definition.submit_label == "Register"
    assert block.definition.cancel_label == "Skip"
    assert len(block.definition.fields) == 3

    # Check fields
    username_field = block.definition.fields[0]
    assert username_field.name == "username"
    assert username_field.field_type == "text"
    assert username_field.required is True
    assert username_field.validation["min_length"] == 3

    email_field = block.definition.fields[1]
    assert email_field.name == "email"
    assert email_field.field_type == "email"

    subscribe_field = block.definition.fields[2]
    assert subscribe_field.name == "subscribe"
    assert subscribe_field.field_type == "yesno"
    assert subscribe_field.required is False


@pytest.mark.asyncio
async def test_all_yaml_parsing() -> None:
    """Test that all content models can parse YAML directly."""
    # Test data as YAML strings
    test_cases = [
        (YesNoContent, 'prompt: "Continue?"'),
        (ChoiceContent, 'prompt: "Pick one:"\noptions: ["A", "B", "C"]'),
        (MultiChoiceContent, 'prompt: "Pick many:"\noptions: ["X", "Y", "Z"]'),
        (InputContent, 'prompt: "Enter text:"\nplaceholder: "Type here"'),
        (ScaleContent, 'prompt: "Rate:"\nlabels:\n  1: "Bad"\n  5: "Good"'),
        (RankingContent, 'prompt: "Order:"\nitems: ["First", "Second", "Third"]'),
        (ConfirmContent, 'prompt: "Sure?"\nmessage: "This is permanent"'),
    ]

    for content_class, yaml_str in test_cases:
        content = content_class.parse(yaml_str)
        assert content.raw_content == yaml_str
        assert hasattr(content, "prompt")
        assert content.prompt is not None


if __name__ == "__main__":
    asyncio.run(test_yesno_block())
