#!/usr/bin/env python3
"""
Textual Chat Interface with Seamless Stream Transitions

A Textual-based TUI chat interface demonstrating seamless stream transitions
where interruptions are invisible to the user.

Key Features:
- Textual TUI with auto-scrolling chat display
- Enter: Send message
- Seamless transitions: Interrupting mid-stream smoothly transitions to new instruction
- No visible cancellation or restart messages
- Character-by-character streaming with smooth updates
- Multi-turn conversation with context preservation
- Status indicator showing stream state

Controls:
- Enter: Send message in input field
- Ctrl+C / q: Quit application

Behavior:
1. User asks: "Write a long essay about AI in English"
2. LLM starts streaming the essay
3. Mid-stream, user sends: "Change to French"
4. Stream **seamlessly transitions** from English to French
5. No "cancelled" message, no visible interruption - smooth continuation

Example transition:
"...neural networks have revolutionized AI. Les réseaux de neurones ont également transformé..."

This demonstrates a production-ready chat interface where sending a message during
streaming creates a natural, seamless transition - just like ChatGPT or Claude.

Technical Highlights:
- RichLog widget for auto-scrolling message display
- Input widget with on_input_submitted() handler
- Worker pattern for async LLM streaming with silent cancellation
- Transition prompt engineering for smooth continuity
- Partial response preservation before interruption
- asyncio.CancelledError for clean cancellation without UI feedback
- Character-by-character text updates
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import TYPE_CHECKING, ClassVar

from google import genai  # type: ignore[import-not-found]
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Footer, Header, Input, RichLog, Static

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from hother.streamblocks import Registry, StreamBlockProcessor, TextDeltaEvent
from hother.streamblocks.syntaxes.markdown import MarkdownFrontmatterSyntax

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

from textual.worker import Worker, WorkerCancelled


class SimpleStreamController:
    """Simple stream controller for Gemini chat - no pause/resume."""

    def __init__(self, api_key: str, model_id: str = "gemini-2.5-flash") -> None:
        """Initialize the stream controller.

        Args:
            api_key: Google API key
            model_id: Model to use
        """
        self.client = genai.Client(api_key=api_key)  # type: ignore[attr-defined]
        self.model_id = model_id
        self.chat = None  # Chat object created on first stream() call

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


class ChatApp(App[None]):
    """Simple Textual chat interface with cancellation on new messages."""

    CSS = """
    Screen {
        background: $surface;
    }

    #status {
        background: $boost;
        color: $text;
        padding: 0 1;
        text-align: center;
        height: 1;
    }

    #status.streaming {
        background: $success;
    }

    #status.ready {
        background: $primary;
    }

    #chat-container {
        height: 1fr;
        border: solid $primary;
        margin: 1;
    }

    #chat-log {
        height: 100%;
        background: $surface;
    }

    #user-input {
        dock: bottom;
        margin: 0 1 1 1;
        border: solid $accent;
    }
    """

    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("q", "quit", "Quit"),
    ]

    def __init__(self, api_key: str) -> None:
        """Initialize the chat app.

        Args:
            api_key: Gemini API key
        """
        super().__init__()
        self.api_key = api_key
        self.controller = SimpleStreamController(api_key)
        self.processor = StreamBlockProcessor(Registry(syntax=MarkdownFrontmatterSyntax()))
        self.is_streaming = False
        self.current_worker: Worker[None] | None = None
        self.current_assistant_response = ""  # Accumulate current response
        self.partial_response_before_interrupt = ""  # Save partial response on interrupt

    def compose(self) -> ComposeResult:
        """Compose the UI layout."""
        yield Header()
        yield Static("Ready - Type your message below", id="status", classes="ready")
        yield VerticalScroll(
            RichLog(id="chat-log", highlight=True, markup=True, wrap=True),
            id="chat-container",
        )
        yield Input(placeholder="Type your message and press Enter...", id="user-input")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the app on mount."""
        # Focus the input field
        self.query_one("#user-input", Input).focus()

        # Show welcome message
        chat_log = self.query_one("#chat-log", RichLog)
        chat_log.write("[bold cyan]Welcome to Textual Chat with Seamless Transitions![/bold cyan]")
        chat_log.write("[dim]Type messages and press Enter to send[/dim]")
        chat_log.write("[dim]Send a message during streaming for seamless transition[/dim]")
        chat_log.write("[dim]Example: 'Write essay' → mid-stream → 'Change to French'[/dim]")
        chat_log.write("[dim]Press q or Ctrl+C to quit[/dim]\n")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle user message submission.

        Args:
            event: Input submitted event
        """
        message = event.value.strip()
        if not message:
            return

        # Clear input
        event.input.clear()

        # Display user message
        chat_log = self.query_one("#chat-log", RichLog)
        chat_log.write(f"[bold cyan]You:[/bold cyan] {message}\n")

        # If streaming, capture partial response and cancel silently
        if self.is_streaming and self.current_worker:
            # Save what was said so far (for seamless transition)
            self.partial_response_before_interrupt = self.current_assistant_response

            # Cancel current stream silently (no UI message!)
            self.current_worker.cancel()
            try:
                await self.current_worker.wait()  # Wait for cancellation to complete
            except WorkerCancelled:
                # Expected when we cancel - ignore
                pass
            # NO cancellation message - seamless transition!

        # Start new stream
        chat_log.write("[bold green]Assistant:[/bold green] ")
        self.is_streaming = True
        self._update_status("streaming")
        self.current_assistant_response = ""

        # Start streaming worker
        self.current_worker = self.run_worker(self.stream_response(message), exclusive=True)

    def _update_status(self, state: str) -> None:
        """Update the status bar.

        Args:
            state: Status state (streaming/ready)
        """
        status = self.query_one("#status", Static)
        status.remove_class("streaming", "ready")
        status.add_class(state)

        if state == "streaming":
            status.update("🔄 Streaming...")
        else:
            status.update("✅ Ready - Type your message below")

    async def stream_response(self, user_message: str) -> None:
        """Stream LLM response with seamless transition support.

        Args:
            user_message: User's message to send to LLM
        """
        chat_log = self.query_one("#chat-log", RichLog)

        # Create prompt with transition context if there was an interruption
        if self.partial_response_before_interrupt:
            # Smooth transition prompt
            prompt = f"""You were responding and said:

{self.partial_response_before_interrupt}

The user now wants: {user_message}

IMPORTANT: Continue NATURALLY and SMOOTHLY. Don't say "Let me start over" or acknowledge the interruption. Just continue your response, transitioning organically to fulfill the new requirement. Make it feel like one continuous thought that naturally evolves.

Example of GOOD transition (English→French):
"...neural networks have revolutionized AI. Les réseaux de neurones ont également transformé..."

Example of BAD transition (too explicit):
"...neural networks. Okay, let me now switch to French and restart..."

Continue now:"""
            # Clear partial response after using it
            self.partial_response_before_interrupt = ""
        else:
            # Normal message (no interruption)
            prompt = user_message

        try:
            # Process stream with the appropriate prompt
            async for event in self.processor.process_stream(self.controller.stream(prompt)):
                # Text delta events - character-by-character rendering
                if isinstance(event, TextDeltaEvent):
                    # Write to RichLog (no newline - continuous text)
                    chat_log.write(event.delta, scroll_end=True)
                    # Accumulate response
                    self.current_assistant_response += event.delta

            # Stream completed successfully
            chat_log.write("\n\n")
            self.is_streaming = False
            self._update_status("ready")

        except asyncio.CancelledError:
            # Stream was cancelled by new message
            # Don't update status here - the new stream will handle it
            raise

        except Exception as e:
            # Error occurred
            chat_log.write(f"\n[red]❌ Error: {e}[/red]\n")
            self.is_streaming = False
            self._update_status("ready")


async def main() -> None:
    """Run the Textual chat interface."""
    # Check API key
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ Error: Set GOOGLE_API_KEY or GEMINI_API_KEY")
        print("Get your key at: https://aistudio.google.com/apikey")
        return

    # Run the app
    app = ChatApp(api_key)
    await app.run_async()


if __name__ == "__main__":
    asyncio.run(main())
