#!/usr/bin/env python3
"""Language Switching with Local LLM Studio - KV Cache Optimized.

This example demonstrates:
- Seamless language switching with local LLM Studio endpoint
- KV cache optimization for immediate reactions
- OpenAI-compatible streaming API
- Full message history preservation
- Same UX as Example 08, but with local LLMs
- No API costs, full privacy, works offline

Endpoint Configuration:
- Default: http://localhost:1234/v1 (LM Studio)
- Compatible with: LM Studio, LocalAI, vLLM, Text Generation WebUI
- Uses OpenAI Chat Completions API format

KV Cache Benefits:
- Full message history sent = server caches attention keys/values
- Fast continuation without recomputing previous tokens
- Immediate reactions to user input
- Efficient partial response transitions

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
- AsyncOpenAI with custom base_url for local endpoints
- OpenAIAdapter for chunk format handling
- Worker.cancel() for silent stream cancellation
- WorkerCancelled exception handling without UI feedback
- Manual message history for KV cache optimization
- Partial response preservation before language switch
- Transition prompt engineering for natural continuity
- Button variant updates for visual state

Usage:
    # 1. Start LM Studio and load a model
    # 2. Enable server in LM Studio (default: localhost:1234)

    # 3. Set environment variables
    export LLM_STUDIO_URL="http://localhost:1234/v1"
    export LLM_STUDIO_MODEL="openai/gpt-oss-20b"

    # 4. Run example
    uv run python examples/live_feedback/09_language_switching_local_llm.py

This mimics ChatGPT/Claude's seamless stream modification behavior using local LLMs.
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import TYPE_CHECKING, Any, ClassVar

from openai import AsyncOpenAI
from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Button, Footer, Header, RichLog, Static

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from hother.streamblocks import OpenAIAdapter, Registry, StreamBlockProcessor, TextDeltaEvent
from hother.streamblocks.syntaxes.markdown import MarkdownFrontmatterSyntax

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

from textual.worker import Worker, WorkerCancelled

# ================================
# Helper Functions
# ================================


def _extract_last_sentence(text: str) -> tuple[str, str]:
    """Extract last complete sentence from text for KV cache priming.

    Args:
        text: Full text to split

    Returns:
        (main_text, last_sentence) - text split before last complete sentence

    Example:
        >>> _extract_last_sentence("First. Second. Third")
        ("First. Second.", "Third")
    """
    if not text:
        return ("", "")

    # Find all sentence-ending punctuation positions
    sentence_ends = []
    for i, char in enumerate(text):
        if char in ".!?" and i < len(text) - 1:
            sentence_ends.append(i)

    # Need at least 2 sentences to split
    if len(sentence_ends) < 2:
        # Fallback: use last 100 characters as primer
        if len(text) > 100:
            return (text[:-100].strip(), text[-100:].strip())
        # Not enough content, return empty main and full text as primer
        return ("", text.strip())

    # Split at second-to-last sentence ending
    split_point = sentence_ends[-2] + 1
    main = text[:split_point].strip()
    last = text[split_point:].strip()

    return (main, last)


# ================================
# Stream Controller
# ================================


class LocalLLMController:
    """Stream controller for local LLM Studio with KV cache optimization."""

    def __init__(
        self,
        base_url: str = "http://localhost:1234/v1",
        model: str = "local-model",
        temperature: float = 0.7,
    ) -> None:
        """Initialize controller.

        Args:
            base_url: LM Studio endpoint URL
            model: Model name from LM Studio
            temperature: Sampling temperature
        """
        self.client = AsyncOpenAI(
            base_url=base_url,
            api_key="not-needed",  # Local servers don't validate
        )
        self.model = model
        self.temperature = temperature
        self.messages: list[dict[str, str]] = []  # Manual history for KV cache
        self._current_response = ""

    async def stream(self, message: str) -> AsyncIterator[Any]:
        """Stream response from local LLM.

        Args:
            message: User message

        Yields:
            OpenAI ChatCompletionChunk objects
        """
        # Add user message to history (enables KV cache)
        self.messages.append({"role": "user", "content": message})

        # Create stream with full history (server caches keys/values)
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=self.messages,
            stream=True,
            temperature=self.temperature,
            max_tokens=-1,  # LM Studio: unlimited (-1)
        )

        # Stream and collect response for history
        self._current_response = ""
        async for chunk in stream:
            # Extract text from chunk
            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if delta.content:
                    self._current_response += delta.content

            yield chunk

        # Add assistant response to history (for next KV cache)
        if self._current_response:
            self.messages.append({"role": "assistant", "content": self._current_response})


# ================================
# Textual App
# ================================


class LanguageSwitchingApp(App[None]):
    """Language switching TUI application with local LLM."""

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

    def __init__(self, base_url: str, model: str) -> None:
        """Initialize the app.

        Args:
            base_url: LM Studio endpoint URL
            model: Model name
        """
        super().__init__()
        self.base_url = base_url
        self.model = model
        self.controller = LocalLLMController(base_url=base_url, model=model)
        self.processor = StreamBlockProcessor(Registry(syntax=MarkdownFrontmatterSyntax()))
        self.adapter = OpenAIAdapter()  # Explicit adapter for OpenAI format
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

        yield Static(f"Ready - Click a language to start streaming (Model: {self.model})", id="status")

        # Essay display area
        yield VerticalScroll(
            RichLog(id="essay-display", highlight=True, markup=True, wrap=True),
            id="essay-container",
        )

        yield Footer()

    def on_mount(self) -> None:
        """Initialize on mount."""
        essay_display = self.query_one("#essay-display", RichLog)
        essay_display.write("[bold cyan]Language Switching Demo - Local LLM[/bold cyan]\n")
        essay_display.write(f"[dim]Endpoint: {self.base_url}[/dim]\n")
        essay_display.write(f"[dim]Model: {self.model}[/dim]\n\n")
        essay_display.write("[dim]Click a language button to start streaming a comprehensive essay about AI[/dim]\n")
        essay_display.write("[dim]Click another language mid-stream for seamless transition[/dim]\n\n")
        essay_display.write("[yellow]Demonstration of KV cache-optimized seamless stream modification[/yellow]\n\n")

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

        # Save current essay if switching to different language (whether streaming or completed)
        if language != self.current_language and self.current_essay:
            self.partial_essay_before_switch = self.current_essay

            # If streaming, cancel and add partial to history
            if self.is_streaming and self.current_worker:
                # Cancel current stream silently
                self.current_worker.cancel()
                try:
                    await self.current_worker.wait()
                except WorkerCancelled:
                    pass  # Expected - no UI message for seamless transition

                # Add partial response to message history using 3-message priming pattern
                # This is CRITICAL for KV cache optimization:
                # 1. Main content as assistant message (KV cache preserved)
                # 2. Language switch instruction as user message
                # 3. Last sentence as assistant message (primes continuation point)

                # Split partial into main content and last sentence (primer)
                main, primer = _extract_last_sentence(self.partial_essay_before_switch)

                # Add main content
                if main:
                    self.controller.messages.append({"role": "assistant", "content": main})

                # Add language switch instruction
                self.controller.messages.append(
                    {"role": "user", "content": f"Continue in {language} from where you stopped"}
                )

                # Add primer to force exact continuation
                if primer:
                    self.controller.messages.append({"role": "assistant", "content": primer})
            # If not streaming, message already in history (stream completed successfully)

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
        # Reset current_essay for new language stream
        # (Previous content already saved in partial and message history)
        # UI RichLog accumulates automatically, so we don't need to track cumulative here
        self.current_essay = ""

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
            # NOTE: Message history already contains:
            # 1. Main content (assistant)
            # 2. "Continue in {language} from where you stopped" (user)
            # 3. Last sentence (assistant - primer)
            # So the prompt can be minimal - the priming does the work
            prompt = f"Continue in {self.current_language}."

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
            # Buffer text to avoid excessive RichLog.write() calls
            # The deltas contain \n that will be interpreted correctly
            buffer = ""
            async for event in self.processor.process_stream(self.controller.stream(prompt), adapter=self.adapter):
                if isinstance(event, TextDeltaEvent):
                    buffer += event.delta
                    self.current_essay += event.delta

                    # Write buffer when it reaches a reasonable size
                    if len(buffer) >= 100:
                        essay_display.write(buffer, scroll_end=True)
                        buffer = ""

            # Write any remaining buffered text
            if buffer:
                essay_display.write(buffer, scroll_end=True)

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
    """Run the language switching demo with local LLM."""
    # Get configuration from environment
    base_url = os.getenv("LLM_STUDIO_URL", "http://localhost:1234/v1")
    model = os.getenv("LLM_STUDIO_MODEL", "local-model")

    # Validate configuration
    print(f"🌐 Endpoint: {base_url}")
    print(f"🤖 Model: {model}")
    print()

    if not base_url or not model:
        print("❌ Error: Missing configuration")
        print()
        print("Set environment variables:")
        print("  export LLM_STUDIO_URL='http://localhost:1234/v1'")
        print("  export LLM_STUDIO_MODEL='openai/gpt-oss-20b'")
        print()
        print("Make sure LM Studio is running with a model loaded!")
        return

    # Run the app
    app = LanguageSwitchingApp(base_url, model)
    await app.run_async()


if __name__ == "__main__":
    asyncio.run(main())
