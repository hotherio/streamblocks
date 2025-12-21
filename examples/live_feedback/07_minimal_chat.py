#!/usr/bin/env python3
"""Minimal chat interface with StreamBlocks and Textual.

This example demonstrates:
- Simple chat UI with boxed messages
- Block-based assistant message extraction
- DelimiterFrontmatterSyntax with !!start/!!end
- Split-screen view: Chat (left) and Raw Output (right)
- Message ID tracking for all messages
- Thread tracking: LLM determines thread ID/name based on conversation topic
- Reply-to relationships: Assistant messages reference user message IDs
- Clean, minimal implementation (~450 lines)

Usage:
    export GEMINI_API_KEY="your-key-here"
    uv run python examples/live_feedback/07_minimal_chat.py

The split screen shows:
- Left: Chat messages in boxes (user=cyan/left, assistant=green/right)
  * User: "You (#1)" shows message ID
  * Assistant: "Assistant (#2) - Thread Name" shows message ID and thread
  * Subtitle: Shows thread ID and reply-to reference
- Right: Raw LLM output stream with !!start/!!end delimiters and thread metadata

Thread Tracking:
- LLM analyzes each message and assigns appropriate thread ID/name
- Examples: "python_help", "debugging", "general_chat"
- Thread names are human-readable: "Python Programming Help", "Bug Fixing"
- Conversation changes create new threads automatically
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import TYPE_CHECKING, ClassVar, Literal

from google import genai  # type: ignore[import-not-found]
from pydantic import Field
from rich import box
from rich.align import Align
from rich.panel import Panel
from textual.app import App, ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Footer, Header, Input, RichLog, Static

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from hother.streamblocks import Registry, StreamBlockProcessor
from hother.streamblocks.core.models import BaseContent, BaseMetadata, Block
from hother.streamblocks.core.types import BlockExtractedEvent, TextDeltaEvent
from hother.streamblocks.syntaxes.delimiter import DelimiterFrontmatterSyntax

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from textual.worker import Worker


# ================================
# Block Definition
# ================================


class MessageMetadata(BaseMetadata):
    """Metadata for chat messages with thread tracking."""

    block_type: Literal["message"] = "message"
    thread_id: str  # LLM-determined thread identifier
    thread_name: str  # Human-readable thread name
    reply_to_message_id: int  # Which user message this replies to


class MessageContent(BaseContent):
    """Minimal content - just raw text."""

    @classmethod
    def parse(cls, raw_text: str) -> MessageContent:
        """Parse message content.

        Args:
            raw_text: The message text

        Returns:
            Parsed content object
        """
        return cls(raw_content=raw_text.strip())


# Create block type
Message = Block[MessageMetadata, MessageContent]


# ================================
# System Prompt
# ================================

SYSTEM_PROMPT = """You are a helpful AI assistant.

═══════════════════════════════════════════════════════════════════
MANDATORY FORMAT - USE THIS FOR EVERY SINGLE RESPONSE - NO EXCEPTIONS
═══════════════════════════════════════════════════════════════════

!!start
---
id: msg_001
block_type: message
thread_id: thread_identifier
thread_name: Thread Name
reply_to_message_id: 1
---
Your response text here.
!!end

═══════════════════════════════════════════════════════════════════
CRITICAL: EVERY RESPONSE MUST HAVE ALL FOUR PARTS
═══════════════════════════════════════════════════════════════════

1. !!start          <-- REQUIRED - Start delimiter
2. YAML metadata    <-- REQUIRED - Between --- markers
3. Response text    <-- REQUIRED - Your actual answer
4. !!end            <-- REQUIRED - End delimiter - DO NOT FORGET THIS

WARNING: If you forget !!end, your response will NOT be displayed to the user!

═══════════════════════════════════════════════════════════════════
METADATA FIELDS - ALL REQUIRED
═══════════════════════════════════════════════════════════════════

id: msg_XXX
  - Increment for each response (msg_001, msg_002, msg_003, etc.)

block_type: message
  - ALWAYS set to "message" (never change this)

thread_id: simple_identifier
  - Keep it SIMPLE - use "general_chat" for most conversations
  - Use "code_help" if the user is asking about programming
  - Use "debugging" if they have a bug
  - DON'T OVERTHINK THIS - when in doubt, use "general_chat"

thread_name: Simple Name
  - Use "General Conversation" for most topics
  - Use "Programming Help" for code questions
  - Use "Bug Fixing" for debugging
  - KEEP IT SIMPLE - don't spend mental energy on this

reply_to_message_id: N
  - The message ID from the user (given in brackets like "[Message ID: 1]")
  - Extract the number and use it here

═══════════════════════════════════════════════════════════════════
CRITICAL: AFTER WRITING YOUR RESPONSE, ALWAYS ADD !!end
═══════════════════════════════════════════════════════════════════

This is ESPECIALLY important when dealing with NEW topics/threads.
Don't let thread creation distract you from closing the block properly.

THE LAST THING YOU WRITE MUST BE: !!end

Your workflow:
1. Write !!start
2. Write YAML metadata (don't overthink thread assignment)
3. Write your response content
4. Write !!end  ← YOUR LAST ACTION - NEVER FORGET

═══════════════════════════════════════════════════════════════════
COMPLETE EXAMPLES - STUDY THESE CAREFULLY
═══════════════════════════════════════════════════════════════════

Example 1 - First message about Python:
User: "[Message ID: 1] Can you help me with Python?"

YOUR RESPONSE MUST BE:
!!start
---
id: msg_001
block_type: message
thread_id: code_help
thread_name: Programming Help
reply_to_message_id: 1
---
Of course! I'd be happy to help you with Python. What specific topic or problem are you working on?
!!end

✓ Notice: Ends with !!end ← CRITICAL - DON'T FORGET THIS


Example 2 - Continuing same thread:
User: "[Message ID: 3] How do I use lists?"

YOUR RESPONSE MUST BE:
!!start
---
id: msg_002
block_type: message
thread_id: code_help
thread_name: Programming Help
reply_to_message_id: 3
---
Lists in Python are ordered collections that you define with square brackets. For example:

my_list = [1, 2, 3, 4, 5]

You can access elements by index, add items with append(), and iterate with for loops.
!!end

✓ Notice: Same thread (still code_help), and ends with !!end ← REMEMBER THIS


Example 3 - New topic (debugging):
User: "[Message ID: 5] I have a bug in my code"

YOUR RESPONSE MUST BE:
!!start
---
id: msg_003
block_type: message
thread_id: debugging
thread_name: Bug Fixing
reply_to_message_id: 5
---
I'll help you debug that. Can you share the error message or describe what's happening?
!!end

✓ Notice: NEW thread (debugging) - BUT STILL ENDS WITH !!end ← ESPECIALLY CRITICAL FOR NEW THREADS!


═══════════════════════════════════════════════════════════════════
BEFORE SENDING - VERIFY THIS CHECKLIST
═══════════════════════════════════════════════════════════════════

☐ 1. Response starts with !!start
☐ 2. First --- appears after !!start
☐ 3. All 5 YAML fields are present (id, block_type, thread_id, thread_name, reply_to_message_id)
☐ 4. Second --- appears after YAML
☐ 5. Response text appears after second ---
☐ 6. Response ends with !!end  <-- CRITICAL - CHECK THIS

═══════════════════════════════════════════════════════════════════
FINAL REMINDER - READ THIS BEFORE EVERY RESPONSE
═══════════════════════════════════════════════════════════════════

EVERY response must follow this pattern EXACTLY:

!!start
---
[all 5 YAML fields - keep thread assignment simple]
---
[your response text]
!!end  ← THE LAST THING YOU WRITE - ALWAYS

SPECIAL WARNING FOR NEW THREADS:
When you create a NEW thread_id/thread_name, you STILL must end with !!end
Don't get distracted by thread creation - ALWAYS close with !!end

If your response doesn't have !!end, it will fail to display to the user.

Your last line MUST be:
!!end
"""


# ================================
# Stream Controller
# ================================


class GeminiController:
    """Simple controller for Gemini streaming."""

    def __init__(self, api_key: str, model_id: str = "gemini-2.5-flash") -> None:
        """Initialize the controller.

        Args:
            api_key: Google API key
            model_id: Model to use
        """
        self.client = genai.Client(api_key=api_key)  # type: ignore[attr-defined]
        self.model_id = model_id
        self.chat = None

    async def stream(self, message: str) -> AsyncIterator[str]:
        """Stream a response from Gemini.

        Args:
            message: User message

        Yields:
            Text chunks from the LLM
        """
        # Create chat on first message
        if self.chat is None:
            config = genai.types.GenerateContentConfig(  # type: ignore[attr-defined]
                system_instruction=SYSTEM_PROMPT, temperature=1.0
            )
            self.chat = self.client.aio.chats.create(model=self.model_id, config=config)  # type: ignore[attr-defined]

        # Stream response
        async for chunk in await self.chat.send_message_stream(message):  # type: ignore[attr-defined]
            if chunk.text:
                yield chunk.text


# ================================
# Textual App
# ================================


class MinimalChatApp(App[None]):
    """Minimal chat application with StreamBlocks."""

    CSS = """
    Screen {
        background: $surface;
    }

    #status {
        dock: top;
        height: 1;
        background: $primary;
        color: $text;
        content-align: center middle;
        text-style: bold;
    }

    #split-view {
        height: 1fr;
        margin: 1;
    }

    #chat-container {
        width: 1fr;
        height: 100%;
        border: solid $primary;
        margin-right: 1;
    }

    #raw-container {
        width: 1fr;
        height: 100%;
        border: solid $accent;
    }

    #chat, #raw {
        height: 100%;
        background: $surface;
    }

    #user-input {
        dock: bottom;
        margin: 0 1 1 1;
    }
    """

    BINDINGS: ClassVar[list[tuple[str, str, str]]] = [
        ("q", "quit", "Quit"),
    ]

    def __init__(self, api_key: str) -> None:
        """Initialize the app.

        Args:
            api_key: Google API key
        """
        super().__init__()

        # Components
        self.controller = GeminiController(api_key)

        # Register Message block with fence syntax
        syntax = DelimiterFrontmatterSyntax(start_delimiter="!!start", end_delimiter="!!end")
        registry = Registry(syntax=syntax)
        registry.register("message", Message)
        self.processor = StreamBlockProcessor(registry)

        # State
        self.is_streaming = False
        self.current_worker: Worker[None] | None = None
        self.message_counter = 0  # Track all messages (user + assistant)

    def compose(self) -> ComposeResult:
        """Compose the UI layout."""
        yield Header()
        yield Static("Minimal Chat - Chat (left) | Raw Output (right)", id="status")

        with Horizontal(id="split-view"):
            yield VerticalScroll(
                RichLog(id="chat", highlight=True, markup=True, wrap=True),
                id="chat-container",
            )
            yield VerticalScroll(
                RichLog(id="raw", highlight=True, markup=True, wrap=True),
                id="raw-container",
            )

        yield Input(placeholder="Type your message and press Enter...", id="user-input")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the app on mount."""
        # Focus the input field
        self.query_one("#user-input", Input).focus()

        # Show welcome message in Chat view (left)
        chat = self.query_one("#chat", RichLog)
        welcome = Panel(
            "[bold]Welcome to Minimal Chat![/bold]\n\n"
            "This demo shows:\n"
            "• Clean chat interface with boxed messages\n"
            "• Block-based message extraction\n"
            "• Real-time streaming from Gemini\n"
            "• Split view: Chat + Raw Output\n\n"
            "Type a message below to start!",
            title="[bold cyan]Chat View[/]",
            title_align="left",
            border_style="cyan",
            box=box.DOUBLE,
        )
        chat.write(welcome, scroll_end=True)
        chat.write("\n")

        # Show info in Raw Output view (right)
        raw = self.query_one("#raw", RichLog)
        raw.write("[bold cyan]Raw LLM Output[/bold cyan]\n", scroll_end=True)
        raw.write("[dim]This shows the unprocessed stream from the LLM,[/dim]\n", scroll_end=True)
        raw.write("[dim]including !!start/!!end delimiters and YAML metadata.[/dim]\n\n", scroll_end=True)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle user message submission.

        Args:
            event: Input submitted event
        """
        message = event.value.strip()
        if not message or self.is_streaming:
            return

        # Clear input
        event.input.clear()

        # Increment message counter and store current message ID
        self.message_counter += 1
        current_msg_id = self.message_counter

        # Display user message in Chat view (boxed, left-aligned with message ID)
        chat = self.query_one("#chat", RichLog)
        user_panel = Panel(
            message,
            title=f"[cyan]You (#{current_msg_id})[/]",
            title_align="left",
            border_style="cyan",
            box=box.ROUNDED,
            width=80,
        )
        chat.write(user_panel, scroll_end=True)
        chat.write("\n")

        # Display user message in Raw Output (plain text with message ID)
        raw = self.query_one("#raw", RichLog)
        raw.write(f"[dim cyan]>>> USER (#{current_msg_id}):[/dim cyan]\n{message}\n\n", scroll_end=True)

        # Debug logging
        print(f"📨 User message #{current_msg_id}: {message[:50]}...")

        # Send to LLM with message ID context
        full_message = f"[Message ID: {current_msg_id}] {message}"

        # Start streaming response
        self.is_streaming = True
        self.current_worker = self.run_worker(self.stream_response(full_message), exclusive=True)

    async def stream_response(self, user_message: str) -> None:
        """Stream a response from the LLM.

        Args:
            user_message: The user's message
        """
        chat = self.query_one("#chat", RichLog)
        raw = self.query_one("#raw", RichLog)

        try:
            # Debug: Log that we're starting
            print("🔄 Starting LLM stream")

            # Write header to raw output
            raw.write("[dim green]<<< ASSISTANT:[/dim green]\n", scroll_end=True)

            # Process stream and extract blocks
            async for event in self.processor.process_stream(self.controller.stream(user_message)):
                if isinstance(event, TextDeltaEvent):
                    # Stream raw text to Raw Output tab
                    raw.write(event.delta, scroll_end=True)

                elif isinstance(event, BlockExtractedEvent):
                    # Block extracted - display in green box in Chat view (right-aligned)
                    block = event.block
                    content = block.content.raw_content
                    metadata = block.metadata

                    # Increment message counter for assistant message
                    self.message_counter += 1
                    assistant_msg_id = self.message_counter

                    print(f"✅ Block extracted: {content[:50]}...")
                    print(f"   Thread: {metadata.thread_name} ({metadata.thread_id})")
                    print(f"   Reply to: #{metadata.reply_to_message_id}")

                    # Create title with message ID and thread name
                    title = f"[green]Assistant (#{assistant_msg_id}) - {metadata.thread_name}[/]"
                    # Create subtitle with thread ID and reply-to info
                    subtitle = f"[dim]Thread: {metadata.thread_id} | ↩ #{metadata.reply_to_message_id}[/dim]"

                    assistant_panel = Panel(
                        content,
                        title=title,
                        subtitle=subtitle,
                        title_align="right",
                        border_style="green",
                        box=box.ROUNDED,
                        width=80,
                    )
                    chat.write(Align.right(assistant_panel), scroll_end=True)
                    chat.write("\n")

                    # Add marker to raw output with thread info
                    raw.write(
                        f"\n[dim green]<<< BLOCK EXTRACTED: {metadata.thread_name} "
                        f"(Thread: {metadata.thread_id}, Reply to: #{metadata.reply_to_message_id}) >>>[/dim green]\n\n",
                        scroll_end=True,
                    )

            self.is_streaming = False
            print("✓ Stream completed")

        except Exception as e:
            # Display error in UI
            print(f"❌ Error: {e}")
            import traceback

            traceback.print_exc()

            chat.write(f"\n[red]❌ Error: {e}[/red]\n\n", scroll_end=True)
            raw.write(f"\n[red]❌ Error: {e}[/red]\n\n", scroll_end=True)
            self.is_streaming = False


# ================================
# Main
# ================================


async def main() -> None:
    """Run the minimal chat interface."""
    # Check API key
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ Error: Set GOOGLE_API_KEY or GEMINI_API_KEY")
        print("Get your key at: https://aistudio.google.com/apikey")
        return

    # Run the app
    app = MinimalChatApp(api_key)
    await app.run_async()


if __name__ == "__main__":
    asyncio.run(main())
