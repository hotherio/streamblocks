#!/usr/bin/env python3
"""
Simple Keyboard Pause Example

A minimalist example showing how to pause/resume an LLM stream with Space key.

Key Features:
- Press Space to pause stream immediately
- Press Space again to resume from where you left off
- Character-by-character live text streaming (typewriter effect)
- Native Gemini event display (chunks, token counts)
- Simple toggle pattern - perfect for quick interruptions

This is the simplest pause/resume pattern demonstrating stream control
during LLM generation.
"""

from __future__ import annotations

import asyncio
import os
import sys
import threading
from typing import TYPE_CHECKING

from google import genai  # type: ignore[import-not-found]
from pynput import keyboard
from rich.console import Console
from rich.panel import Panel

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from hother.streamblocks import Registry, StreamBlockProcessor, TextDeltaEvent
from hother.streamblocks.syntaxes.markdown import MarkdownFrontmatterSyntax

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

# Rich console for beautiful output
console = Console()


class SimpleKeyboardPause:
    """Minimal Gemini stream with keyboard pause/resume control."""

    def __init__(self, api_key: str, model_id: str = "gemini-2.5-flash") -> None:
        """Initialize the stream controller.

        Args:
            api_key: Google API key
            model_id: Model to use
        """
        self.client = genai.Client(api_key=api_key)  # type: ignore[attr-defined]
        self.model_id = model_id
        self.chat = None  # Chat object created on first stream() call
        # Async event for pause request
        self._pause_requested = asyncio.Event()
        # Threading events for thread-async coordination
        self._paused_confirm = threading.Event()  # Stream confirms it's paused
        self._resume_ready = threading.Event()  # Thread signals resume
        # Persistent flag to track if stream was interrupted (survives coordination cycle)
        self._stream_interrupted = False
        # Accumulate text during streaming (for pause/resume)
        self._accumulated_text = ""

    def request_pause(self) -> None:
        """Request pause and wait for confirmation.

        Called from keyboard listener thread. Blocks until stream confirms pause.
        """
        self._pause_requested.set()
        # Block until stream confirms it's paused
        self._paused_confirm.wait()
        self._paused_confirm.clear()

    def resume(self) -> None:
        """Resume the stream."""
        self._resume_ready.set()

    def accumulate_text(self, text: str) -> None:
        """Accumulate text during streaming.

        Args:
            text: Text delta to accumulate
        """
        self._accumulated_text += text

    def was_paused(self) -> bool:
        """Check if stream was interrupted by pause.

        Returns:
            True if stream was interrupted by pause, False if it ended naturally
        """
        return self._stream_interrupted

    async def stream(self, prompt: str) -> AsyncIterator:  # type: ignore[type-arg]
        """Stream from Gemini using Chat API with pause capability.

        Args:
            prompt: Initial prompt (only used on first call)

        Yields:
            Gemini chunks
        """
        # Reset interrupt flag at start of each iteration
        self._stream_interrupted = False

        # Create chat session on first call
        if self.chat is None:
            self.chat = self.client.aio.chats.create(model=self.model_id)  # type: ignore[attr-defined]
            message = prompt
            # Start fresh accumulation
            self._accumulated_text = ""
        elif self._accumulated_text:
            # Resuming after pause - tell LLM what it said so far and to continue
            accumulated_copy = self._accumulated_text
            self._accumulated_text = ""

            message = f"""You were in the middle of your response. Here's what you said so far:

{accumulated_copy}

Please continue from exactly where you left off. Do not repeat what you already said, just continue naturally."""
        else:
            # Should not happen, but handle gracefully
            message = "Please continue from where you left off."

        try:
            # Stream the message through Chat API (maintains history automatically)
            async for chunk in await self.chat.send_message_stream(message):  # type: ignore[attr-defined]
                # Check for pause request
                if self._pause_requested.is_set():
                    # Mark stream as interrupted (persistent flag for main loop)
                    self._stream_interrupted = True

                    # Confirm pause to thread
                    self._paused_confirm.set()
                    self._pause_requested.clear()

                    # Wait for resume signal
                    while not self._resume_ready.is_set():
                        await asyncio.sleep(0.1)
                    self._resume_ready.clear()

                    # Exit stream - will be restarted by main loop with new message
                    return

                # Yield chunk
                yield chunk

        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            return


def space_key_listener(controller: SimpleKeyboardPause) -> None:
    """Listen for Space key presses to toggle pause/resume.

    Args:
        controller: Stream controller to pause/resume
    """
    console.print("[dim]Press Space to pause/resume...[/dim]")

    paused = False

    def on_press(key: keyboard.Key | keyboard.KeyCode | None) -> None:
        """Handle key press events.

        Args:
            key: The key that was pressed (None if key cannot be determined)
        """
        nonlocal paused

        # Ignore None keys
        if key is None:
            return

        # Check if Space was pressed
        is_space = False
        try:
            # Try keyboard.Key.space first (special key)
            if key == keyboard.Key.space:
                is_space = True
        except AttributeError:
            # Try character comparison for regular keys
            if hasattr(key, "char") and key.char == " ":  # type: ignore[attr-defined]
                is_space = True

        if is_space:
            if not paused:
                # Pause the stream
                console.print("\n[yellow]⏸️  Paused[/yellow]")
                controller.request_pause()
                paused = True
            else:
                # Resume the stream
                controller.resume()
                console.print("[green]▶️  Resumed[/green]")
                console.print("[dim]Press Space to pause/resume...[/dim]\n")
                paused = False

    # Start pynput keyboard listener (runs in background thread)
    listener = keyboard.Listener(on_press=on_press)
    listener.start()

    # Keep thread alive
    try:
        listener.join()
    except KeyboardInterrupt:
        listener.stop()


async def main() -> None:
    """Run the simple keyboard pause example."""
    # Welcome panel
    console.print(
        Panel(
            (
                "[bold cyan]Simple Keyboard Pause Example[/bold cyan]\n\n"
                "[yellow]• Press Space anytime to pause[/yellow]\n"
                "[yellow]• Press Space again to resume[/yellow]\n"
                "[yellow]• Native Gemini events shown with 🔵[/yellow]"
            ),
            title="⏸️  Space Key Control",
            border_style="cyan",
        )
    )

    # Check API key
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        console.print("[red]❌ Error: Set GOOGLE_API_KEY or GEMINI_API_KEY[/red]")
        return

    # Create controller
    controller = SimpleKeyboardPause(api_key)

    # Create minimal processor with character-by-character streaming
    syntax = MarkdownFrontmatterSyntax()
    registry = Registry(syntax=syntax)
    processor = StreamBlockProcessor(registry)  # emit_text_deltas=True by default

    # Prompt - Make it long enough for user to have time to pause
    prompt = """You are a helpful AI assistant with deep expertise in machine learning.
Please provide a comprehensive, detailed explanation of how neural networks work.

Your explanation should include:
1. A clear introduction to what neural networks are and why they're important in modern AI
2. The biological inspiration behind neural networks and how they mimic the human brain
3. The basic structure: neurons, layers (input, hidden, output), weights, biases, and activation functions
4. How training works: forward propagation, loss functions, backpropagation, and gradient descent
5. Different types of neural networks (feedforward, CNN, RNN, transformers) with specific examples
6. Real-world applications with concrete examples (image recognition, natural language processing, etc.)
7. Common challenges and limitations (overfitting, training time, data requirements, interpretability)

Make your explanation 6-7 comprehensive paragraphs long with concrete examples and analogies
to help explain complex concepts. Include historical context where relevant. Take your time to
be thorough and detailed."""

    console.print(Panel(prompt, title="📝 Task", border_style="dim"))
    console.print()

    # Track listener initialization
    listener_started = False

    # Keep processing until stream completes naturally
    while True:
        stream_ended_naturally = True

        # Process stream with character-by-character display
        async for event in processor.process_stream(controller.stream(prompt)):
            # Start space key listener on first event (inside the loop!)
            if not listener_started:
                listener_thread = threading.Thread(target=space_key_listener, args=(controller,), daemon=True)
                listener_thread.start()
                listener_started = True

            # Native Gemini chunks (passed through)
            if processor.is_native_event(event):
                # Extract and display Gemini-specific information
                text = getattr(event, "text", None)
                if text:
                    # Show preview of native chunk (first 40 chars)
                    preview = repr(text)[:40]
                    print(f"\r🔵 Gemini Chunk: {preview}", end="")
                    sys.stdout.flush()

                # Show token usage if available
                usage = getattr(event, "usage_metadata", None)
                if usage:
                    total = getattr(usage, "total_token_count", None)
                    if total:
                        print(f" | 📊 Tokens: {total}")
                        sys.stdout.flush()

            # Text delta events (character-by-character)
            elif isinstance(event, TextDeltaEvent):
                # Show each character immediately (typewriter effect)
                sys.stdout.write(event.delta)
                sys.stdout.flush()
                # Accumulate text for pause/resume
                controller.accumulate_text(event.delta)

            # Check if stream was paused (ended early)
            if controller.was_paused():
                stream_ended_naturally = False

        # If stream ended naturally (no pause), we're done
        if stream_ended_naturally:
            break

        # Otherwise, stream was paused and will resume in next iteration

    console.print("\n")
    console.print("[bold green]✅ Stream completed![/bold green]")


if __name__ == "__main__":
    asyncio.run(main())
