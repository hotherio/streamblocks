"""Interactive UI demo using Textual for responding to StreamBlocks."""

import asyncio
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

import yaml
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.widgets import (
    Button,
    Checkbox,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    RadioButton,
    RadioSet,
    Select,
    Static,
)

from hother.streamblocks import DelimiterFrontmatterSyntax, Registry, StreamBlockProcessor
from hother.streamblocks.core.models import Block
from hother.streamblocks.core.types import BlockEndEvent, BlockErrorEvent
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


class InteractiveWidget(Static):
    """Base class for interactive block widgets."""

    def __init__(self, block: Block[Any, Any]) -> None:
        super().__init__()
        self.block = block
        self.response: Any = None


class YesNoWidget(InteractiveWidget):
    """Widget for yes/no questions."""

    def compose(self) -> ComposeResult:
        yield Label(f"❓ {self.block.content.prompt}", classes="prompt")
        with Horizontal(classes="button-group"):
            yield Button(self.block.metadata.yes_label, id="yes", variant="primary")
            yield Button(self.block.metadata.no_label, id="no", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        self.response = event.button.id == "yes"
        self.app.handle_response(self.block.metadata.id, self.response)  # type: ignore[attr-defined]


class ChoiceWidget(InteractiveWidget):
    """Widget for single choice questions."""

    def compose(self) -> ComposeResult:
        yield Label(f"🔘 {self.block.content.prompt}", classes="prompt")

        if self.block.metadata.display_style == "dropdown":
            options = [(opt, opt) for opt in self.block.content.options]
            yield Select(options, prompt="Select an option", id="choice-select")
        else:
            with RadioSet(id="choice-radio"):
                for opt in self.block.content.options:
                    yield RadioButton(opt)

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle dropdown selection."""
        self.response = str(event.value)
        self.app.handle_response(self.block.metadata.id, self.response)  # type: ignore[attr-defined]

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        """Handle radio button selection."""
        if event.pressed:
            self.response = str(event.pressed.label)
            self.app.handle_response(self.block.metadata.id, self.response)  # type: ignore[attr-defined]


class MultiChoiceWidget(InteractiveWidget):
    """Widget for multiple choice questions."""

    def __init__(self, block: Block[Any, Any]) -> None:
        super().__init__(block)
        self.selected: set[str] = set()

    def compose(self) -> ComposeResult:
        yield Label(f"☑️  {self.block.content.prompt}", classes="prompt")
        if self.block.metadata.min_selections > 1 or self.block.metadata.max_selections:
            yield Label(
                f"Select {self.block.metadata.min_selections}-{self.block.metadata.max_selections or 'all'} options",
                classes="hint",
            )

        with Container(id="checkbox-group"):
            for i, opt in enumerate(self.block.content.options):
                yield Checkbox(opt, id=f"check-{i}", value=False)

        yield Button("Submit", id="submit", variant="primary")

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Handle checkbox changes."""
        option = str(event.checkbox.label)
        if event.value:
            self.selected.add(option)
        else:
            self.selected.discard(option)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle submit button."""
        if event.button.id == "submit" and (
            self.block.metadata.min_selections
            <= len(self.selected)
            <= (self.block.metadata.max_selections or float("inf"))
        ):
            self.response = list(self.selected)
            self.app.handle_response(self.block.metadata.id, self.response)  # type: ignore[attr-defined]


class InputWidget(InteractiveWidget):
    """Widget for text input."""

    def compose(self) -> ComposeResult:
        yield Label(f"📝 {self.block.content.prompt}", classes="prompt")
        yield Input(placeholder=self.block.content.placeholder, value=self.block.content.default_value, id="text-input")
        yield Button("Submit", id="submit", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle submit button."""
        if event.button.id == "submit":
            input_widget = self.query_one("#text-input", Input)
            value = input_widget.value

            # Basic validation
            if len(value) >= self.block.metadata.min_length:
                if self.block.metadata.max_length is None or len(value) <= self.block.metadata.max_length:
                    self.response = value
                    self.app.handle_response(self.block.metadata.id, self.response)  # type: ignore[attr-defined]


class ScaleWidget(InteractiveWidget):
    """Widget for scale rating."""

    def compose(self) -> ComposeResult:
        yield Label(f"⭐ {self.block.content.prompt}", classes="prompt")

        with RadioSet(id="scale-radio"):
            for value in range(
                self.block.metadata.min_value, self.block.metadata.max_value + 1, self.block.metadata.step
            ):
                label = self.block.content.labels.get(value, str(value))
                yield RadioButton(f"{value} - {label}")

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        """Handle radio button selection."""
        if event.pressed:
            # Extract value from label
            value_str = str(event.pressed.label).split(" - ")[0]
            self.response = int(value_str)
            self.app.handle_response(self.block.metadata.id, self.response)  # type: ignore[attr-defined]


class RankingWidget(InteractiveWidget):
    """Widget for ranking items."""

    def compose(self) -> ComposeResult:
        yield Label(f"🔢 {self.block.content.prompt}", classes="prompt")
        yield Label("Use ↑/↓ to move items, Space to select", classes="hint")

        list_view = ListView(id="ranking-list")
        for item in self.block.content.items:
            list_view.append(ListItem(Label(item)))
        yield list_view

        yield Button("Submit Ranking", id="submit", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle submit button."""
        if event.button.id == "submit":
            list_view = self.query_one("#ranking-list", ListView)
            ranked_items: list[Any] = []
            for item in list_view.children:
                if isinstance(item, ListItem):
                    label = item.query_one(Label)
                    ranked_items.append(label.renderable)  # type: ignore[attr-defined]

            self.response = ranked_items
            self.app.handle_response(self.block.metadata.id, self.response)  # type: ignore[attr-defined]


class ConfirmWidget(InteractiveWidget):
    """Widget for confirmation dialogs."""

    def compose(self) -> ComposeResult:
        yield Label(f"⚠️  {self.block.content.prompt}", classes="prompt")
        yield Label(self.block.content.message, classes="message")

        with Horizontal(classes="button-group"):
            variant = "error" if self.block.metadata.danger_mode else "primary"
            yield Button(self.block.metadata.confirm_label, id="confirm", variant=variant)
            yield Button(self.block.metadata.cancel_label, id="cancel", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        self.response = event.button.id == "confirm"
        self.app.handle_response(self.block.metadata.id, self.response)  # type: ignore[attr-defined]


class FormWidget(InteractiveWidget):
    """Widget for form blocks."""

    def __init__(self, block: Block[Any, Any]) -> None:
        super().__init__(block)
        self.form_data: dict[str, Any] = {}

    def compose(self) -> ComposeResult:
        yield Label(f"📋 {self.block.content.prompt}", classes="prompt")

        with Container(id="form-fields"):
            for field in self.block.content.fields:
                yield Label(f"{field.label}{' *' if field.required else ''}")

                if field.field_type == "text":
                    yield Input(id=f"field-{field.name}")
                elif field.field_type == "yesno":
                    with RadioSet(id=f"field-{field.name}"):
                        yield RadioButton("Yes")
                        yield RadioButton("No")
                # Add more field types as needed

        with Horizontal(classes="button-group"):
            yield Button(self.block.metadata.submit_label, id="submit", variant="primary")
            yield Button(self.block.metadata.cancel_label, id="cancel", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "submit":
            # Collect form data
            self.response = self.form_data  # Simplified for demo
            self.app.handle_response(self.block.metadata.id, self.response)  # type: ignore[attr-defined]
        elif event.button.id == "cancel":
            self.app.handle_response(self.block.metadata.id, None)  # type: ignore[attr-defined]


class ResponseHistory(Static):
    """Widget showing response history."""

    def __init__(self) -> None:
        super().__init__()
        self.responses: list[tuple[str, str, Any]] = []

    def add_response(self, block_id: str, timestamp: str, response: Any) -> None:
        """Add a response to history."""
        self.responses.append((block_id, timestamp, response))
        self.refresh()

    def render(self) -> str:
        """Render the response history."""
        if not self.responses:
            return "[dim]No responses yet[/dim]"

        lines: list[str] = []
        for block_id, timestamp, response in self.responses[-10:]:  # Show last 10
            lines.append(f"[cyan]{timestamp}[/cyan] {block_id}")
            lines.append(f"  Response: {response}")
            lines.append("")

        return "\n".join(lines)


class InteractiveBlocksApp(App[None]):
    """Textual app for interactive blocks."""

    CSS = """
    Horizontal {
        height: 100%;
    }

    #active-widgets {
        width: 60%;
        border: solid cyan;
        padding: 1;
        height: 100%;
        overflow-y: scroll;
    }

    #response-history {
        width: 40%;
        border: solid green;
        padding: 1;
        height: 100%;
        overflow-y: scroll;
    }

    #widget-container {
        height: auto;
        min-height: 100%;
    }

    #widget-spacer {
        height: 1fr;
        min-height: 1;
    }

    #history {
        height: auto;
    }

    .title {
        text-style: bold;
        margin: 0 0 1 0;
        dock: top;
    }

    .prompt {
        margin: 1 0;
        text-style: bold;
    }

    .hint {
        margin: 0 0 1 0;
        color: $text-muted;
    }

    .message {
        margin: 1;
        padding: 1;
        background: $surface;
    }

    .button-group {
        margin: 1 0;
        height: 3;
    }

    #checkbox-group {
        height: auto;
        margin: 0 0 1 0;
    }

    InteractiveWidget {
        height: auto;
        margin: 0 0 1 0;
        padding: 1;
        border: solid $primary;
    }

    Checkbox {
        height: auto;
        margin: 0;
        padding: 0 1;
    }

    RadioSet {
        height: auto;
        margin: 0;
    }

    RadioButton {
        height: auto;
        margin: 0;
        padding: 0 1;
    }

    Select {
        height: auto;
        margin: 0 0 1 0;
    }

    Input {
        height: auto;
        margin: 0 0 1 0;
    }

    Button {
        height: auto;
    }

    ListView {
        height: auto;
        max-height: 10;
        margin: 0 0 1 0;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self.active_widgets: list[InteractiveWidget] = []
        self.processor: StreamBlockProcessor | None = None
        self.current_block_id: str | None = None

    def compose(self) -> ComposeResult:
        """Create the UI layout."""
        yield Header()

        with Horizontal():
            with VerticalScroll(id="active-widgets", can_focus=True):
                yield Static("Active Widgets (newest at bottom ↓)", classes="title")
                yield Container(id="widget-container")

            with VerticalScroll(id="response-history", can_focus=True):
                yield Static("Response History", classes="title")
                yield Container(id="history")

        yield Footer()

    def on_mount(self) -> None:
        """Start processing blocks when app starts."""
        # Start processing blocks immediately
        self.run_worker(self.process_blocks())

    async def process_blocks(self) -> None:
        """Process the block stream."""
        # Note: This example uses a workaround for dynamic block types

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
        # This is a workaround - in the new design, you'd normally have separate processors
        interactive_syntax = InteractiveSyntax(block_mapping=block_type_mapping)

        # Create type-specific registry
        registry = Registry(syntax=interactive_syntax)

        # Create processor with config
        from hother.streamblocks.core.processor import ProcessorConfig

        config = ProcessorConfig(lines_buffer=10)
        self.processor = StreamBlockProcessor(registry, config=config)

        # Process stream and show widgets as they arrive
        async for event in self.processor.process_stream(demo_stream()):
            if isinstance(event, BlockEndEvent):
                block = event.get_block()
                if block is None:
                    continue
                self.log(f"Extracted block: {block.metadata.id} ({block.metadata.block_type})")
                await self.add_interactive_block(block)
            elif isinstance(event, BlockErrorEvent):
                self.log(f"Block rejected: {event.reason}")

    async def add_interactive_block(self, block: Block[Any, Any]) -> None:
        """Add a new interactive block widget."""
        widget_class = {
            "yesno": YesNoWidget,
            "choice": ChoiceWidget,
            "multichoice": MultiChoiceWidget,
            "input": InputWidget,
            "scale": ScaleWidget,
            "ranking": RankingWidget,
            "confirm": ConfirmWidget,
            "form": FormWidget,
        }.get(block.metadata.block_type)

        if widget_class:
            widget = widget_class(block)
            self.active_widgets.append(widget)

            # Add to UI at the bottom
            container = self.query_one("#widget-container", Container)
            await container.mount(widget)
            self.log(f"Mounted widget for block {block.metadata.id}")

            # Scroll to show the new widget
            scroll_container = self.query_one("#active-widgets", VerticalScroll)
            scroll_container.scroll_to_widget(widget, animate=True)

        else:
            self.log(f"No widget class for block type: {block.metadata.block_type}")

    def handle_response(self, block_id: str, response: Any) -> None:
        """Handle a widget response."""
        # Add to history
        timestamp = datetime.now().strftime("%H:%M:%S")
        history_container = self.query_one("#history", Container)

        # Create a new history entry
        entry = Static(f"[cyan]{timestamp}[/cyan] {block_id}\n  Response: {response}\n", classes="history-entry")
        history_container.mount(entry)

        # Remove widget
        for widget in self.active_widgets:
            if widget.block.metadata.id == block_id:
                self.active_widgets.remove(widget)
                widget.remove()
                break


async def demo_stream() -> AsyncIterator[str]:
    """Demo stream with interactive blocks."""
    text = """!!start
---
id: welcome
block_type: yesno
yes_label: "Let's Start!"
no_label: "Maybe Later"
---
prompt: "Welcome! Would you like to start the interactive demo?"
!!end

[Wait 2 seconds...]

!!start
---
id: theme
block_type: choice
display_style: radio
---
prompt: "Choose your preferred theme:"
options:
  - "Light"
  - "Dark"
  - "Auto"
!!end

[Wait 2 seconds...]

!!start
---
id: features
block_type: multichoice
min_selections: 1
max_selections: 2
---
prompt: "Select features to enable:"
options:
  - "Notifications"
  - "Auto-save"
  - "Spell check"
  - "Syntax highlighting"
!!end

[Wait 2 seconds...]

!!start
---
id: username
block_type: input
min_length: 3
max_length: 20
---
prompt: "What should we call you?"
placeholder: "Enter your name"
!!end

[Wait 2 seconds...]

!!start
---
id: satisfaction
block_type: scale
min_value: 1
max_value: 5
---
prompt: "Rate your experience:"
labels:
  1: "Poor"
  3: "Good"
  5: "Excellent"
!!end
"""

    # Stream in chunks with delays
    # First, process to handle wait markers
    processed_text = ""
    lines = text.split("\n")

    for _i, line in enumerate(lines):
        if line.strip() == "[Wait 2 seconds...]":
            # Yield what we have so far in chunks
            chunk_size = 50
            for j in range(0, len(processed_text), chunk_size):
                chunk = processed_text[j : j + chunk_size]
                yield chunk
                await asyncio.sleep(0.01)
            processed_text = ""  # Reset for next section
            await asyncio.sleep(2)  # Wait
        else:
            processed_text += line + "\n"

    # Yield any remaining text
    if processed_text:
        chunk_size = 50
        for j in range(0, len(processed_text), chunk_size):
            chunk = processed_text[j : j + chunk_size]
            yield chunk
            await asyncio.sleep(0.01)


if __name__ == "__main__":
    app = InteractiveBlocksApp()
    app.run()
