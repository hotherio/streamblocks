#!/usr/bin/env python3
"""
Feedback Patterns with Cancellation Example

An advanced example demonstrating multiple feedback injection patterns with timeout cancellation
and rich keyboard controls.

Key Features:
- Multiple feedback patterns: Quick options, custom text, structured forms
- Timeout cancellation using hother-cancelable (hard stop after 5 minutes)
- Rich keyboard controls with multiple keys
- Questionary integration for beautiful CLI prompts
- Smooth typewriter rendering with instant pause
- Protocol-based feedback patterns for extensibility

Keyboard Controls:
- Space: Quick pause/resume (no feedback)
- f: Structured feedback with predefined options
- c: Custom free-form feedback
- Ctrl+C: Immediate hard cancel
- +/-: Adjust rendering speed
- e: Toggle native events
- q: Graceful quit

This example demonstrates production-ready patterns for interactive LLM applications
with sophisticated feedback injection and cancellation handling.

Technical Highlights:
- FeedbackPattern Protocol for extensible feedback designs
- hother-cancelable integration for timeout management
- Async/await patterns for smooth coordination
- Thread-safe keyboard handling with pynput
- Sub-millisecond pause latency
- Rich UI with panels, tables, and status displays
"""

from __future__ import annotations

import asyncio
import os
import sys
import threading
from typing import TYPE_CHECKING, Protocol

import questionary
from google import genai  # type: ignore[import-not-found]
from hother.cancelable import Cancelable
from pynput import keyboard
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from hother.streamblocks import Registry, StreamBlockProcessor, TextDeltaEvent
from hother.streamblocks.syntaxes.markdown import MarkdownFrontmatterSyntax

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

# Rich console for beautiful output
console = Console()


class FeedbackPattern(Protocol):
    """Protocol for feedback injection patterns.

    Implementations must provide a method to prompt the user for feedback
    with their own UI/UX pattern.
    """

    def prompt_user(self) -> str | None:
        """Prompt user for feedback.

        Returns:
            Feedback text or None to resume without feedback
        """
        ...


class QuickFeedbackPattern:
    """Quick feedback with predefined options.

    Provides fast selection from common feedback types without typing.
    """

    def prompt_user(self) -> str | None:
        """Prompt with quick selection menu.

        Returns:
            Selected feedback or None
        """
        console.print("\n[bold cyan]Quick Feedback Options:[/bold cyan]")

        options = [
            "Continue in more detail",
            "Summarize briefly",
            "Give concrete examples",
            "Provide step-by-step instructions",
            "Skip to next topic",
            "Resume without changes",
        ]

        choice = questionary.select(
            "How should I continue?",
            choices=options,
            style=questionary.Style(
                [
                    ("selected", "fg:cyan bold"),
                    ("pointer", "fg:cyan bold"),
                ]
            ),
        ).ask()

        if choice == "Resume without changes" or choice is None:
            return None

        return choice


class CustomFeedbackPattern:
    """Custom free-form feedback.

    Allows users to type arbitrary feedback text with multiline support.
    """

    def prompt_user(self) -> str | None:
        """Prompt with free-form text input.

        Returns:
            Custom feedback or None
        """
        console.print("\n[bold cyan]Custom Feedback:[/bold cyan]")
        console.print("[dim]Type your feedback (Ctrl+D or empty to skip)[/dim]")

        feedback = questionary.text(
            "Your feedback:",
            multiline=True,
            style=questionary.Style(
                [
                    ("answer", "fg:cyan"),
                ]
            ),
        ).ask()

        if feedback is None or not feedback.strip():
            return None

        return feedback.strip()


class StructuredFeedbackPattern:
    """Structured feedback with multiple fields.

    Collects structured feedback through a series of questions.
    """

    def prompt_user(self) -> str | None:
        """Prompt with structured questions.

        Returns:
            Structured feedback or None
        """
        console.print("\n[bold cyan]Structured Feedback:[/bold cyan]")

        # Direction question
        direction = questionary.select(
            "Change direction?",
            choices=[
                "More technical depth",
                "More examples",
                "Simpler explanation",
                "Different approach",
                "Continue as-is",
            ],
            style=questionary.Style(
                [
                    ("selected", "fg:cyan bold"),
                    ("pointer", "fg:cyan bold"),
                ]
            ),
        ).ask()

        if direction == "Continue as-is" or direction is None:
            return None

        # Follow-up details
        details = questionary.text(
            f"Additional details for '{direction}':",
            style=questionary.Style(
                [
                    ("answer", "fg:cyan"),
                ]
            ),
        ).ask()

        if details and details.strip():
            return f"{direction}. {details.strip()}"

        return direction


class TypewriterRenderer:
    """Smooth character-by-character text renderer with event-driven pause."""

    def __init__(self, char_delay: float = 0.015) -> None:
        """Initialize the typewriter renderer.

        Args:
            char_delay: Delay between characters in seconds
        """
        self._char_delay = char_delay
        self._chars_written = 0
        self._pause_event = asyncio.Event()
        self._pending_text = ""

    async def write_text_delta(self, text: str) -> bool:
        """Display text character by character with instant pause support.

        Args:
            text: Text to display

        Returns:
            True if completed, False if paused mid-rendering
        """
        full_text = self._pending_text + text
        self._pending_text = ""

        for i, char in enumerate(full_text):
            sys.stdout.write(char)
            sys.stdout.flush()
            self._chars_written += 1

            try:
                await asyncio.wait_for(self._pause_event.wait(), timeout=self._char_delay)
            except TimeoutError:
                pass
            else:
                self._pending_text = full_text[i + 1 :]
                return False

        return True

    def request_pause(self) -> None:
        """Request immediate pause of rendering."""
        self._pause_event.set()

    def resume(self) -> None:
        """Resume rendering."""
        self._pause_event.clear()

    @property
    def char_delay(self) -> float:
        """Current delay between characters."""
        return self._char_delay

    def set_speed(self, delay: float) -> None:
        """Adjust rendering speed."""
        self._char_delay = max(0.001, min(0.1, delay))

    @property
    def chars_written(self) -> int:
        """Total characters written."""
        return self._chars_written


class SimpleKeyboardPause:
    """Minimal Gemini stream with keyboard pause/resume and cancellation."""

    def __init__(self, api_key: str, model_id: str = "gemini-2.5-flash") -> None:
        """Initialize the stream controller.

        Args:
            api_key: Google API key
            model_id: Model to use
        """
        self.client = genai.Client(api_key=api_key)  # type: ignore[attr-defined]
        self.model_id = model_id
        self.chat = None
        self._pause_requested = asyncio.Event()
        self._paused_confirm = threading.Event()
        self._resume_ready = threading.Event()
        self._stream_interrupted = False
        self._accumulated_text = ""
        self._feedback: str | None = None

    def request_pause(self) -> None:
        """Request pause and wait for confirmation."""
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
            True if stream was interrupted by pause
        """
        return self._stream_interrupted

    async def stream(self, prompt: str, cancel: Cancelable | None = None) -> AsyncIterator:  # type: ignore[type-arg]
        """Stream from Gemini with pause capability and optional cancellation.

        Args:
            prompt: Initial prompt
            cancel: Optional Cancelable for timeout cancellation

        Yields:
            Gemini chunks
        """
        self._stream_interrupted = False

        if self.chat is None:
            self.chat = self.client.aio.chats.create(model=self.model_id)  # type: ignore[attr-defined]
            message = prompt
            self._accumulated_text = ""
        elif self._accumulated_text:
            accumulated_copy = self._accumulated_text
            self._accumulated_text = ""

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
            message = "Please continue from where you left off."

        try:
            async for chunk in await self.chat.send_message_stream(message):  # type: ignore[attr-defined]
                # Check for hard cancellation
                if cancel and cancel.is_cancelled:
                    console.print("\n[yellow]⏹️  Stream cancelled (timeout)[/yellow]")
                    raise asyncio.CancelledError()

                # Check for pause request
                if self._pause_requested.is_set():
                    self._stream_interrupted = True
                    self._paused_confirm.set()
                    self._pause_requested.clear()

                    while not self._resume_ready.is_set():
                        await asyncio.sleep(0.1)
                    self._resume_ready.clear()
                    return

                yield chunk

        except asyncio.CancelledError:
            return
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            return


def enhanced_keyboard_listener(
    controller: SimpleKeyboardPause,
    renderer: TypewriterRenderer,
    show_events: dict[str, bool],
    feedback_patterns: dict[str, FeedbackPattern],
) -> None:
    """Listen for keyboard controls with feedback pattern selection.

    Args:
        controller: Stream controller
        renderer: Text renderer
        show_events: Event display state
        feedback_patterns: Available feedback patterns
    """
    console.print("[dim]Controls: Space=pause, f=feedback, c=custom, +/-=speed, e=events, q=quit[/dim]")

    paused = False

    def on_press(key: keyboard.Key | keyboard.KeyCode | None) -> None:
        """Handle key press events.

        Args:
            key: The key that was pressed
        """
        nonlocal paused

        if key is None:
            return

        # Space key: Quick pause/resume (no feedback)
        if key == keyboard.Key.space:
            if not paused:
                console.print("\n[yellow]⏸️  Paused[/yellow]")
                renderer.request_pause()
                controller.request_pause()
                paused = True
            else:
                renderer.resume()
                controller.resume()
                console.print("[green]▶️  Resumed (no feedback)[/green]")
                console.print("[dim]Controls: Space=pause, f=feedback, c=custom, q=quit[/dim]\n")
                paused = False
            return

        # Character keys
        if hasattr(key, "char"):
            char = key.char  # type: ignore[attr-defined]

            # f key: Structured feedback
            if char == "f":
                if not paused:
                    console.print("\n[yellow]⏸️  Paused for feedback[/yellow]")
                    renderer.request_pause()
                    controller.request_pause()
                    paused = True

                # Prompt for feedback (blocking - runs in thread)
                feedback = feedback_patterns["quick"].prompt_user()

                if feedback:
                    controller.inject_feedback(feedback)
                    console.print(f"[green]✅ Feedback: {feedback}[/green]")
                else:
                    console.print("[yellow]⏭️  Resuming without feedback[/yellow]")

                renderer.resume()
                controller.resume()
                console.print("[dim]Controls: Space=pause, f=feedback, c=custom, q=quit[/dim]\n")
                paused = False

            # c key: Custom feedback
            elif char == "c":
                if not paused:
                    console.print("\n[yellow]⏸️  Paused for custom feedback[/yellow]")
                    renderer.request_pause()
                    controller.request_pause()
                    paused = True

                # Prompt for custom feedback
                feedback = feedback_patterns["custom"].prompt_user()

                if feedback:
                    controller.inject_feedback(feedback)
                    console.print(f"[green]✅ Custom feedback: {feedback[:50]}...[/green]")
                else:
                    console.print("[yellow]⏭️  Resuming without feedback[/yellow]")

                renderer.resume()
                controller.resume()
                console.print("[dim]Controls: Space=pause, f=feedback, c=custom, q=quit[/dim]\n")
                paused = False

            # e key: Toggle native events
            elif char == "e":
                show_events["enabled"] = not show_events["enabled"]
                status = "enabled" if show_events["enabled"] else "disabled"
                console.print(f"\nℹ️  Native events [bold]{status}[/bold]")

            # +/= keys: Faster rendering
            elif char in ["+", "="]:
                new_delay = renderer.char_delay * 0.8
                renderer.set_speed(new_delay)
                speed = 1 / new_delay
                console.print(f"\n⚡ Speed: [bold]{speed:.0f}[/bold] chars/sec")

            # - key: Slower rendering
            elif char == "-":
                new_delay = renderer.char_delay * 1.2
                renderer.set_speed(new_delay)
                speed = 1 / new_delay
                console.print(f"\n🐌 Speed: [bold]{speed:.0f}[/bold] chars/sec")

            # q key: Quit
            elif char == "q":
                console.print("\n\n[yellow]👋 Exiting...[/yellow]")
                sys.exit(0)

    # Start pynput keyboard listener
    listener = keyboard.Listener(on_press=on_press)
    listener.start()

    try:
        listener.join()
    except KeyboardInterrupt:
        listener.stop()


async def main() -> None:
    """Run the feedback patterns with cancellation example."""
    # Welcome panel
    console.print(
        Panel(
            (
                "[bold cyan]Feedback Patterns with Cancellation Example[/bold cyan]\n\n"
                "[yellow]Controls:[/yellow]\n"
                "  • [bold]Space[/bold]: Quick pause/resume (no feedback)\n"
                "  • [bold]f[/bold]: Structured feedback with quick options\n"
                "  • [bold]c[/bold]: Custom free-form feedback\n"
                "  • [bold]+ / -[/bold]: Adjust rendering speed\n"
                "  • [bold]e[/bold]: Toggle native events\n"
                "  • [bold]q[/bold]: Quit\n"
                "  • [bold]Ctrl+C[/bold]: Hard cancel\n\n"
                "[dim]Timeout: 5 minutes (adjustable)[/dim]"
            ),
            title="⌨️  Interactive Feedback & Cancellation",
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

    # Create renderer
    renderer = TypewriterRenderer(char_delay=0.015)
    show_events = {"enabled": False}  # Disabled by default for cleaner output

    # Create feedback patterns
    feedback_patterns: dict[str, FeedbackPattern] = {
        "quick": QuickFeedbackPattern(),
        "custom": CustomFeedbackPattern(),
        "structured": StructuredFeedbackPattern(),
    }

    # Display initial speed
    speed = 1 / renderer.char_delay
    console.print(f"\n💨 Rendering speed: [bold]{speed:.0f}[/bold] chars/sec")
    console.print("⏱️  Timeout: [bold]5 minutes[/bold]\n")

    # Create processor
    syntax = MarkdownFrontmatterSyntax()
    registry = Registry(syntax=syntax)
    processor = StreamBlockProcessor(registry)

    # Comprehensive prompt
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

    # Process with timeout cancellation (5 minutes)
    async with Cancelable.with_timeout(300.0) as cancel:
        try:
            while True:
                stream_ended_naturally = True

                async for event in processor.process_stream(controller.stream(prompt, cancel=cancel)):
                    # Start keyboard listener on first event
                    if not listener_started:
                        listener_thread = threading.Thread(
                            target=enhanced_keyboard_listener,
                            args=(controller, renderer, show_events, feedback_patterns),
                            daemon=True,
                        )
                        listener_thread.start()
                        listener_started = True

                    # Native Gemini chunks (optional display)
                    if processor.is_native_event(event):
                        if show_events["enabled"]:
                            text = getattr(event, "text", None)
                            if text:
                                preview = repr(text)[:30]
                                console.print(f"[dim]🔵 Chunk: {preview}...[/dim]")

                    # Text delta events - SMOOTH rendering
                    elif isinstance(event, TextDeltaEvent):
                        await renderer.write_text_delta(event.delta)
                        controller.accumulate_text(event.delta)

                    # Check if stream was paused
                    if controller.was_paused():
                        stream_ended_naturally = False

                # If stream ended naturally, we're done
                if stream_ended_naturally:
                    break

        except asyncio.CancelledError:
            console.print("\n\n[yellow]⏹️  Operation timed out (5 minutes)[/yellow]")

    # Final statistics
    console.print("\n")
    table = Table(title="📊 Session Statistics", show_header=False, border_style="cyan")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="bold green")

    table.add_row("Characters written", f"{renderer.chars_written:,}")
    table.add_row("Final speed", f"{1 / renderer.char_delay:.0f} chars/sec")
    table.add_row("Character delay", f"{renderer.char_delay * 1000:.1f}ms")

    console.print(table)
    console.print("\n[bold green]✅ Session completed![/bold green]")


if __name__ == "__main__":
    asyncio.run(main())
