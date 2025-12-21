#!/usr/bin/env python3
"""Language Switching During LLM Streaming - Seamless Mid-Stream Transitions.

This example demonstrates:
- Textual TUI with language selection buttons
- LLM streams a comprehensive essay about AI history
- Click language buttons to switch mid-stream
- Seamless transitions - no visible cancellation messages
- Essay continues naturally in the new language
- Worker cancellation pattern for silent stream switching

Features:
- Three language options: English, French, Spanish
- Horizontal button layout with visual feedback
- Real-time streaming with character-by-character display
- Smart prompt engineering for natural language transitions
- Status bar showing current streaming state

Controls:
- Click language buttons: Switch language mid-stream
- q: Quit application

Expected Behavior:
1. Click English → Essay starts in English
2. Mid-stream, click French → Seamless transition to French
3. Essay continues from same point, different language
4. No "cancelled" or "restarting" messages

Technical Highlights:
- Worker.cancel() for silent stream cancellation
- WorkerCancelled exception handling without UI feedback
- Partial response preservation before language switch
- Transition prompt engineering for natural continuity
- Button variant updates for visual state

Usage:
    export GEMINI_API_KEY="your-key-here"
    uv run python examples/live_feedback/08_language_switching.py

This mimics ChatGPT/Claude's seamless stream modification behavior.
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import TYPE_CHECKING, ClassVar

from google import genai  # type: ignore[import-not-found]
from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Button, Footer, Header, RichLog, Static

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from hother.streamblocks import Registry, StreamBlockProcessor, TextDeltaEvent
from hother.streamblocks.syntaxes.markdown import MarkdownFrontmatterSyntax

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

from textual.worker import Worker, WorkerCancelled

# ================================
# Stream Controller
# ================================


class SimpleStreamController:
    """Simple stream controller for Gemini chat."""

    def __init__(self, api_key: str, model_id: str = "gemini-2.5-flash") -> None:
        """Initialize the stream controller.

        Args:
            api_key: Google API key
            model_id: Model to use
        """
        self.client = genai.Client(api_key=api_key)  # type: ignore[attr-defined]
        self.model_id = model_id
        self.chat = None

    async def stream(self, message: str) -> AsyncIterator:  # type: ignore[type-arg]
        """Stream from Gemini chat API.

        Args:
            message: User message to send

        Yields:
            Gemini chunks
        """
        # Create chat session on first call
        if self.chat is None:
            self.chat = self.client.aio.chats.create(model=self.model_id)  # type: ignore[attr-defined]

        # Stream the message (Chat API maintains history automatically)
        async for chunk in await self.chat.send_message_stream(message):  # type: ignore[attr-defined]
            yield chunk


# ================================
# Textual App
# ================================


class LanguageSwitchingApp(App[None]):
    """Language switching TUI application."""

    CSS = """
    #language-buttons {
        height: auto;
        padding: 1;
        background: $boost;
        dock: top;
    }

    #language-buttons Button {
        margin: 0 1;
    }

    #status {
        background: $primary;
        color: $text;
        padding: 0 1;
        text-align: center;
        height: 1;
    }

    #status.streaming {
        background: $success;
    }

    #essay-container {
        height: 1fr;
        border: solid $primary;
        margin: 1;
    }

    #essay-display {
        height: 100%;
        background: $surface;
    }
    """

    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("q", "quit", "Quit"),
    ]

    def __init__(self, api_key: str) -> None:
        """Initialize the app.

        Args:
            api_key: Gemini API key
        """
        super().__init__()
        self.api_key = api_key
        self.controller = SimpleStreamController(api_key)
        self.processor = StreamBlockProcessor(Registry(syntax=MarkdownFrontmatterSyntax()))
        self.is_streaming = False
        self.current_worker: Worker[None] | None = None
        self.current_language = "English"
        self.current_essay = ""  # Accumulate essay text
        self.partial_essay_before_switch = ""  # For seamless transition

    def compose(self) -> ComposeResult:
        """Compose UI layout."""
        yield Header()

        # Language buttons at top
        with Horizontal(id="language-buttons"):
            yield Button("🇬🇧 English", id="btn-english", variant="primary")
            yield Button("🇫🇷 French", id="btn-french")
            yield Button("🇪🇸 Spanish", id="btn-spanish")

        yield Static("Ready - Click a language to start streaming", id="status")

        # Essay display area
        yield VerticalScroll(
            RichLog(id="essay-display", highlight=True, markup=True, wrap=True),
            id="essay-container",
        )

        yield Footer()

    def on_mount(self) -> None:
        """Initialize on mount."""
        essay_display = self.query_one("#essay-display", RichLog)
        essay_display.write("[bold cyan]Language Switching Demo[/bold cyan]\n")
        essay_display.write("[dim]Click a language button to start streaming a comprehensive essay about AI[/dim]\n")
        essay_display.write("[dim]Click another language mid-stream for seamless transition[/dim]\n\n")
        essay_display.write("[yellow]Demonstration of ChatGPT/Claude-style seamless stream modification[/yellow]\n\n")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle language button clicks.

        Args:
            event: Button pressed event
        """
        button_id = event.button.id

        # Map button to language
        language_map = {
            "btn-english": "English",
            "btn-french": "French",
            "btn-spanish": "Spanish",
        }

        new_language = language_map.get(button_id)
        if new_language:
            await self.switch_language(new_language)

            # Update button variants - highlight active language
            for btn_id, lang in language_map.items():
                btn = self.query_one(f"#{btn_id}", Button)
                btn.variant = "primary" if lang == new_language else "default"

    async def switch_language(self, language: str) -> None:
        """Switch to new language, cancelling current stream if active.

        Args:
            language: Language to switch to
        """
        # If already in this language and not streaming, start fresh
        if language == self.current_language and not self.is_streaming:
            await self.start_essay(language)
            return

        # If streaming, cancel and transition seamlessly
        if self.is_streaming and self.current_worker:
            # Save partial essay for seamless transition
            self.partial_essay_before_switch = self.current_essay

            # Cancel current stream silently
            self.current_worker.cancel()
            try:
                await self.current_worker.wait()
            except WorkerCancelled:
                pass  # Expected - no UI message for seamless transition

        # Update language
        self.current_language = language

        # Start new stream
        essay_display = self.query_one("#essay-display", RichLog)
        if self.partial_essay_before_switch:
            essay_display.write(f"\n[bold green]→ Continuing in {language}...[/bold green]\n\n")
        else:
            essay_display.write(f"[bold cyan]Starting essay in {language}...[/bold cyan]\n\n")

        self.is_streaming = True
        self._update_status(f"Streaming in {language}...")
        # Continue from where we left off
        self.current_essay = self.partial_essay_before_switch

        self.current_worker = self.run_worker(self.stream_essay(), exclusive=True)

    async def start_essay(self, language: str) -> None:
        """Start fresh essay in specified language.

        Args:
            language: Language to use
        """
        self.current_language = language
        self.current_essay = ""
        self.partial_essay_before_switch = ""

        essay_display = self.query_one("#essay-display", RichLog)
        essay_display.clear()
        essay_display.write(f"[bold cyan]Starting essay in {language}...[/bold cyan]\n\n")

        self.is_streaming = True
        self._update_status(f"Streaming in {language}...")

        self.current_worker = self.run_worker(self.stream_essay(), exclusive=True)

    def _update_status(self, message: str) -> None:
        """Update status bar.

        Args:
            message: Status message to display
        """
        status = self.query_one("#status", Static)
        status.update(message)
        if self.is_streaming:
            status.add_class("streaming")
        else:
            status.remove_class("streaming")

    async def stream_essay(self) -> None:
        """Stream essay with seamless language transitions."""
        essay_display = self.query_one("#essay-display", RichLog)

        # Build prompt based on whether this is a transition or fresh start
        if self.partial_essay_before_switch:
            # Seamless transition - continue same essay in new language
            prompt = f"""You were writing an essay about Artificial Intelligence and have written:

{self.partial_essay_before_switch}

Continue THE SAME ESSAY but now write in {self.current_language}.

CRITICAL INSTRUCTIONS:
1. DO NOT restart the essay
2. DO NOT say "Let me switch to {self.current_language}" or acknowledge the language change
3. SEAMLESSLY continue from where you left off, but now in {self.current_language}
4. The transition should be INVISIBLE - as if you were always writing in {self.current_language}

GOOD transition example (English→French):
"...revolutionized the field of AI. Les réseaux de neurones profonds ont également..."

BAD transition example:
"...revolutionized the field. Okay, now I'll switch to French. L'intelligence artificielle..."

Continue the essay now in {self.current_language}:"""

            self.partial_essay_before_switch = ""

        else:
            # Fresh start - new essay in specified language
            prompt = f"""Write a comprehensive, detailed essay about the history and impact of Artificial Intelligence in {self.current_language}.

The essay should be 8-10 paragraphs long and cover:

1. Early history and pioneers of AI (1950s-1980s)
2. AI winters and periods of renewed interest
3. The machine learning revolution (1990s-2010s)
4. Deep learning and neural networks emergence
5. Modern AI applications (computer vision, NLP, robotics)
6. Ethical considerations and societal impact
7. Current challenges and limitations
8. Future prospects and potential developments

Write the entire essay in {self.current_language}. Make it engaging, informative, and comprehensive.
This will take several minutes to complete - write a thorough, detailed essay."""

        try:
            # Stream essay character by character
            async for event in self.processor.process_stream(self.controller.stream(prompt)):
                if isinstance(event, TextDeltaEvent):
                    essay_display.write(event.delta, scroll_end=True)
                    self.current_essay += event.delta

            # Stream completed successfully
            essay_display.write("\n\n")
            self.is_streaming = False
            self._update_status(f"Essay completed in {self.current_language}")

        except asyncio.CancelledError:
            # Cancelled for language switch - don't update status
            # The new stream will handle status updates
            raise

        except Exception as e:
            # Real error occurred
            essay_display.write(f"\n[red]❌ Error: {e}[/red]\n")
            self.is_streaming = False
            self._update_status("Error occurred")


# ================================
# Main
# ================================


async def main() -> None:
    """Run the language switching demo."""
    # Check API key
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ Error: Set GOOGLE_API_KEY or GEMINI_API_KEY")
        print("Get your key at: https://aistudio.google.com/apikey")
        return

    # Run the app
    app = LanguageSwitchingApp(api_key)
    await app.run_async()


if __name__ == "__main__":
    asyncio.run(main())
