#!/usr/bin/env python3
"""
Smooth Typewriter Rendering Example

An advanced example demonstrating smooth character-by-character text rendering
with interactive speed controls and pause/resume functionality.

Key Features:
- Smooth typewriter effect (character-by-character with configurable delay)
- Space key: Pause/Resume stream
- +/- keys: Adjust rendering speed in real-time
- e key: Toggle native event display
- q key: Quit
- Protocol-based renderer design for extensibility
- Live statistics tracking

This example shows how to create a production-ready text renderer that provides
smooth visual feedback during LLM stream generation, with full user control over
rendering speed and display options.

Technical Highlights:
- StreamRenderer Protocol for clean interface design
- TypewriterRenderer with async character-by-character writes
- Sub-millisecond pause latency using asyncio.Event.wait() with timeout
- Pynput keyboard integration for multi-key controls
- Real-time speed adjustment without stream interruption
- Statistics tracking (characters written, speed)
"""

from __future__ import annotations

import asyncio
import os
import sys
import threading
from typing import TYPE_CHECKING, Protocol

from google import genai  # type: ignore[import-not-found]
from pynput import keyboard
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from hother.streamblocks import Registry, StreamBlockProcessor, TextDeltaEvent
from hother.streamblocks.syntaxes.markdown import MarkdownFrontmatterSyntax

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from hother.cancelable import Cancelable

# Rich console for beautiful output
console = Console()


class StreamRenderer(Protocol):
    """Protocol for smooth text rendering.

    Implementations must provide smooth character-by-character rendering
    with configurable speed, immediate write capabilities, and pause/resume support.
    """

    async def write_text_delta(self, text: str) -> bool:
        """Write text smoothly, character by character.

        Args:
            text: Text to display (may contain multiple characters)

        Returns:
            True if completed, False if paused mid-rendering
        """
        ...

    def write_immediate(self, text: str) -> None:
        """Write text immediately without delay.

        Args:
            text: Text to display instantly (for status messages)
        """
        ...

    def request_pause(self) -> None:
        """Request immediate pause of rendering."""
        ...

    def resume(self) -> None:
        """Resume rendering after pause."""
        ...

    @property
    def char_delay(self) -> float:
        """Current delay between characters in seconds."""
        ...

    def set_speed(self, delay: float) -> None:
        """Adjust rendering speed.

        Args:
            delay: New delay between characters in seconds
        """
        ...


class TypewriterRenderer:
    """Smooth character-by-character text renderer.

    Provides typewriter effect with configurable delay between characters,
    preserving all formatting (newlines, spaces, etc.).

    Features:
    - Configurable delay between characters
    - Runtime speed adjustment
    - Statistics tracking
    - Efficient single-character writes
    """

    def __init__(self, char_delay: float = 0.015) -> None:
        """Initialize the typewriter renderer.

        Args:
            char_delay: Delay between characters in seconds (default: 15ms ≈ 67 chars/sec)
        """
        self._char_delay = char_delay
        self._chars_written = 0
        # Event-driven pause support for sub-millisecond latency
        self._pause_event = asyncio.Event()
        self._pending_text = ""

    async def write_text_delta(self, text: str) -> bool:
        """Display text character by character with instant pause support.

        Uses asyncio.Event.wait() with timeout to detect pause immediately
        during character delay, achieving sub-millisecond pause latency.

        Args:
            text: Text to display (may contain multiple characters)

        Returns:
            True if completed normally, False if paused mid-rendering
        """
        # Prepend any pending text from previous pause
        full_text = self._pending_text + text
        self._pending_text = ""

        for i, char in enumerate(full_text):
            # Write character immediately
            sys.stdout.write(char)
            sys.stdout.flush()
            self._chars_written += 1

            # Wait for delay OR pause event (whichever comes first)
            try:
                await asyncio.wait_for(self._pause_event.wait(), timeout=self._char_delay)
            except TimeoutError:
                # Normal: delay finished without pause, continue to next char
                pass
            else:
                # If we get here, pause was set during delay!
                # Save remaining text and exit immediately
                self._pending_text = full_text[i + 1 :]
                return False  # Paused

        return True  # Completed

    def write_immediate(self, text: str) -> None:
        """Write text immediately without delay.

        Args:
            text: Text to display instantly
        """
        sys.stdout.write(text)
        sys.stdout.flush()

    def request_pause(self) -> None:
        """Request immediate pause of rendering.

        Sets the pause event, which causes write_text_delta() to exit
        on the next character check (sub-millisecond latency).
        """
        self._pause_event.set()

    def resume(self) -> None:
        """Resume rendering.

        Clears the pause event. Any pending text will be prepended
        to the next text delta automatically.
        """
        self._pause_event.clear()

    @property
    def char_delay(self) -> float:
        """Current delay between characters in seconds."""
        return self._char_delay

    def set_speed(self, delay: float) -> None:
        """Adjust rendering speed.

        Args:
            delay: New delay between characters (clamped to 1ms-100ms)
        """
        self._char_delay = max(0.001, min(0.1, delay))

    @property
    def chars_written(self) -> int:
        """Total characters written."""
        return self._chars_written


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
        self._paused_confirm = threading.Event()
        self._resume_ready = threading.Event()
        # Persistent flag to track if stream was interrupted
        self._stream_interrupted = False
        # Accumulate text during streaming
        self._accumulated_text = ""
        # Feedback to inject on resume
        self._feedback: str | None = None

    def request_pause(self) -> None:
        """Request pause and wait for confirmation.

        Called from keyboard listener thread. Blocks until stream confirms pause.
        """
        self._pause_requested.set()
        self._paused_confirm.wait()
        self._paused_confirm.clear()

    def resume(self) -> None:
        """Resume the stream."""
        self._resume_ready.set()

    def inject_feedback(self, feedback: str) -> None:
        """Inject feedback to be sent on next resume.

        Args:
            feedback: Feedback text to send to LLM
        """
        self._feedback = feedback

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

    async def stream(self, prompt: str, cancel: Cancelable | None = None) -> AsyncIterator:  # type: ignore[type-arg]
        """Stream from Gemini using Chat API with pause capability and optional cancellation.

        Args:
            prompt: Initial prompt (only used on first call)
            cancel: Optional Cancelable for timeout/hard cancellation

        Yields:
            Gemini chunks
        """
        # Reset interrupt flag at start of each iteration
        self._stream_interrupted = False

        # Create chat session on first call
        if self.chat is None:
            self.chat = self.client.aio.chats.create(model=self.model_id)  # type: ignore[attr-defined]
            message = prompt
            self._accumulated_text = ""
        elif self._accumulated_text:
            # Resuming after pause - tell LLM what it said so far
            accumulated_copy = self._accumulated_text
            self._accumulated_text = ""

            # Check if feedback was injected
            if self._feedback:
                message = f"""You were in the middle of your response. Here's what you said so far:

{accumulated_copy}

User feedback: {self._feedback}

Please acknowledge this feedback and continue from where you left off, incorporating the feedback."""
                self._feedback = None
            else:
                message = f"""You were in the middle of your response. Here's what you said so far:

{accumulated_copy}

Please continue from exactly where you left off. Do not repeat what you already said, just continue naturally."""
        else:
            # Should not happen, but handle gracefully
            message = "Please continue from where you left off."

        try:
            # Stream the message through Chat API (maintains history automatically)
            async for chunk in await self.chat.send_message_stream(message):  # type: ignore[attr-defined]
                # Check for hard cancellation (timeout or external cancel)
                if cancel and cancel.is_cancelled:
                    console.print("\n[yellow]⏹️  Stream cancelled (timeout or user request)[/yellow]")
                    raise asyncio.CancelledError()

                # Check for pause request
                if self._pause_requested.is_set():
                    # Mark stream as interrupted
                    self._stream_interrupted = True
                    # Confirm pause to thread
                    self._paused_confirm.set()
                    self._pause_requested.clear()
                    # Wait for resume signal
                    while not self._resume_ready.is_set():
                        await asyncio.sleep(0.1)
                    self._resume_ready.clear()
                    # Exit stream - will be restarted by main loop
                    return

                # Yield chunk
                yield chunk

        except asyncio.CancelledError:
            # Clean cancellation - don't print error
            return
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            return


def enhanced_keyboard_listener(
    controller: SimpleKeyboardPause,
    renderer: TypewriterRenderer,
    show_events: dict[str, bool],
) -> None:
    """Listen for keyboard controls with multiple keys.

    Args:
        controller: Stream controller for pause/resume
        renderer: Text renderer for speed adjustment
        show_events: Mutable dict to track event display state
    """
    console.print("[dim]Press Space to pause/resume, +/- for speed, e for events, q to quit[/dim]")

    paused = False

    def on_press(key: keyboard.Key | keyboard.KeyCode | None) -> None:
        """Handle key press events.

        Args:
            key: The key that was pressed
        """
        nonlocal paused

        # Ignore None keys
        if key is None:
            return

        # Space key: Pause/Resume
        if key == keyboard.Key.space:
            if not paused:
                console.print("\n[yellow]⏸️  Paused[/yellow]")
                # Pause renderer FIRST (immediate, <1ms latency)
                renderer.request_pause()
                controller.request_pause()
                paused = True
            else:
                # Resume renderer FIRST
                renderer.resume()
                controller.resume()
                console.print("[green]▶️  Resumed[/green]")
                console.print("[dim]Controls: Space=pause, +/-=speed, e=events, q=quit[/dim]\n")
                paused = False
            return

        # Character keys
        if hasattr(key, "char"):
            char = key.char  # type: ignore[attr-defined]

            # e key: Toggle native events
            if char == "e":
                show_events["enabled"] = not show_events["enabled"]
                status = "enabled" if show_events["enabled"] else "disabled"
                console.print(f"\nℹ️  Native events [bold]{status}[/bold]")

            # +/= keys: Faster rendering
            elif char in ["+", "="]:
                new_delay = renderer.char_delay * 0.8  # 20% faster
                renderer.set_speed(new_delay)
                speed = 1 / new_delay
                console.print(f"\n⚡ Speed: [bold]{speed:.0f}[/bold] chars/sec (delay: {new_delay * 1000:.1f}ms)")

            # - key: Slower rendering
            elif char == "-":
                new_delay = renderer.char_delay * 1.2  # 20% slower
                renderer.set_speed(new_delay)
                speed = 1 / new_delay
                console.print(f"\n🐌 Speed: [bold]{speed:.0f}[/bold] chars/sec (delay: {new_delay * 1000:.1f}ms)")

            # q key: Quit
            elif char == "q":
                console.print("\n\n[yellow]👋 Exiting...[/yellow]")
                sys.exit(0)

    # Start pynput keyboard listener
    listener = keyboard.Listener(on_press=on_press)
    listener.start()

    # Keep thread alive
    try:
        listener.join()
    except KeyboardInterrupt:
        listener.stop()


async def main() -> None:
    """Run the smooth typewriter rendering example."""
    # Welcome panel
    console.print(
        Panel(
            (
                "[bold cyan]Smooth Typewriter Rendering Example[/bold cyan]\n\n"
                "[yellow]Controls:[/yellow]\n"
                "  • [bold]Space[/bold]: Pause/Resume\n"
                "  • [bold]+ / -[/bold]: Adjust rendering speed\n"
                "  • [bold]e[/bold]: Toggle native events display\n"
                "  • [bold]q[/bold]: Quit\n\n"
                "[dim]Experience smooth character-by-character rendering[/dim]"
            ),
            title="⌨️  Interactive Typewriter",
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

    # Create renderer with smooth typewriter effect
    renderer = TypewriterRenderer(char_delay=0.015)  # ~67 chars/sec
    show_events = {"enabled": True}

    # Display initial speed
    speed = 1 / renderer.char_delay
    console.print(f"\n💨 Initial speed: [bold]{speed:.0f}[/bold] chars/sec\n")

    # Create minimal processor
    syntax = MarkdownFrontmatterSyntax()
    registry = Registry(syntax=syntax)
    processor = StreamBlockProcessor(registry)

    # Prompt - comprehensive explanation
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

        # Process stream with smooth rendering
        async for event in processor.process_stream(controller.stream(prompt)):
            # Start keyboard listener on first event
            if not listener_started:
                listener_thread = threading.Thread(
                    target=enhanced_keyboard_listener, args=(controller, renderer, show_events), daemon=True
                )
                listener_thread.start()
                listener_started = True

            # Native Gemini chunks (optional display)
            if processor.is_native_event(event):
                if show_events["enabled"]:
                    text = getattr(event, "text", None)
                    if text:
                        preview = repr(text)[:30]
                        console.print(f"[dim]🔵 Chunk: {preview}...[/dim]", style="dim")

                    usage = getattr(event, "usage_metadata", None)
                    if usage:
                        total = getattr(usage, "total_token_count", None)
                        if total:
                            console.print(f"[dim]📊 Tokens: {total}[/dim]")

            # Text delta events - SMOOTH character-by-character rendering
            elif isinstance(event, TextDeltaEvent):
                # Returns False if paused mid-rendering
                await renderer.write_text_delta(event.delta)
                # Always accumulate text (renderer tracks what was written internally)
                controller.accumulate_text(event.delta)

            # Check if stream was paused
            if controller.was_paused():
                stream_ended_naturally = False

        # If stream ended naturally, we're done
        if stream_ended_naturally:
            break

    # Final statistics
    console.print("\n")
    table = Table(title="📊 Rendering Statistics", show_header=False, border_style="cyan")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="bold green")

    table.add_row("Characters written", f"{renderer.chars_written:,}")
    table.add_row("Final speed", f"{1 / renderer.char_delay:.0f} chars/sec")
    table.add_row("Character delay", f"{renderer.char_delay * 1000:.1f}ms")

    console.print(table)
    console.print("\n[bold green]✅ Stream completed![/bold green]")


if __name__ == "__main__":
    asyncio.run(main())
