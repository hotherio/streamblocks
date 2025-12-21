#!/usr/bin/env python3
"""
Multi-Threaded Conversation Management with Single LLM

A sophisticated Textual-based TUI demonstrating how a SINGLE LLM can manage
multiple simultaneous conversation threads with automatic semantic routing.

Key Features:
- Single LLM processes messages sequentially
- Automatic thread assignment based on semantic analysis
- "All Messages" tab showing chronological chat view
- Per-thread filtered tabs (Thread 1: AI, Thread 2: Jokes, etc.)
- Real-time thread discovery and tab creation
- Thread indicators in chronological view ([T1], [T2])
- Structured blocks with routing metadata

Controls:
- Enter: Send message (LLM auto-routes to appropriate thread)
- Tab/Shift+Tab: Switch between tabs
- Ctrl+C / q: Quit application

Behavior:
1. User: "Write an essay on AI" (msg_id=1)
   → LLM decides: thread_id=1 (new topic)
   → Creates "Thread 1: AI" tab

2. User: "Tell me a joke" (msg_id=2)
   → LLM decides: thread_id=2 (unrelated to AI)
   → Creates "Thread 2: Jokes" tab

3. User: "What about neural networks?" (msg_id=3)
   → LLM decides: thread_id=1 (related to AI essay)
   → Routes to existing "Thread 1: AI"

The "All Messages" tab shows everything chronologically with thread badges,
while individual thread tabs show filtered conversations.

Technical Highlights:
- ThreadedAnswer block type with YAML frontmatter metadata
- LLM-as-router pattern (semantic thread assignment)
- Sequential message processing (single LLM, message queue)
- Dual-view UI (chronological + filtered per thread)
- Dynamic tab creation as threads are discovered
- Per-thread context isolation
- TabbedContent widget with RichLog per tab
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar, Literal

from google import genai  # type: ignore[import-not-found]
from pydantic import Field
from rich import box
from rich.panel import Panel
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Footer, Header, Input, RichLog, Static, TabbedContent, TabPane

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from hother.streamblocks import Registry, StreamBlockProcessor
from hother.streamblocks.core.models import BaseContent, BaseMetadata, Block
from hother.streamblocks.core.types import BlockExtractedEvent, TextDeltaEvent
from hother.streamblocks.syntaxes.delimiter import DelimiterFrontmatterSyntax

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from textual.worker import Worker

from textual.worker import WorkerCancelled

# ================================
# Block Type Definition
# ================================


class AnswerMetadata(BaseMetadata):
    """Metadata for conversation responses.

    The LLM outputs this metadata to indicate which thread a response belongs to
    and which user message it's answering.
    """

    block_type: Literal["answer"] = "answer"
    thread_id: int = Field(..., description="Which conversation thread this belongs to")
    message_id: int = Field(..., description="Which user message this answers")
    topic: str = Field(..., description="Brief description of the thread topic")
    reasoning: str = Field(..., description="LLM's explanation for thread assignment")


class AnswerContent(BaseContent):
    """Content for conversation responses."""

    @classmethod
    def parse(cls, raw_text: str) -> AnswerContent:
        """Parse response content.

        Args:
            raw_text: The response text from the LLM

        Returns:
            Parsed content object
        """
        return cls(raw_content=raw_text.strip())


class Answer(Block[AnswerMetadata, AnswerContent]):
    """Answer block configuration.

    This block type is emitted by the LLM to indicate thread routing.
    """


# ================================
# Data Structures
# ================================


@dataclass
class ThreadedMessage:
    """A user message with unique ID."""

    message_id: int
    content: str
    timestamp: float


@dataclass
class ThreadedResponse:
    """An LLM response assigned to a thread."""

    response_id: str
    thread_id: int
    message_id: int
    topic: str
    content: str
    reasoning: str
    timestamp: float


@dataclass
class ConversationThread:
    """A single conversation thread with its own history."""

    thread_id: int
    topic: str
    messages: list[ThreadedMessage] = field(default_factory=list)
    responses: list[ThreadedResponse] = field(default_factory=list)

    def get_context(self) -> str:
        """Build context string for this thread only.

        Returns:
            Formatted context with thread's conversation history
        """
        context_parts = []
        for msg in self.messages:
            context_parts.append(f"User (message_id={msg.message_id}): {msg.content}")
        for resp in self.responses:
            context_parts.append(f"Assistant: {resp.content}")
        return "\n\n".join(context_parts)


class ThreadManager:
    """Manages multiple conversation threads with chronological tracking."""

    def __init__(self) -> None:
        """Initialize the thread manager."""
        self.threads: dict[int, ConversationThread] = {}
        self.next_thread_id = 1
        self.message_counter = 0
        self.all_messages: list[ThreadedMessage] = []  # Chronological
        self.all_responses: list[ThreadedResponse] = []  # Chronological

    def add_user_message(self, content: str) -> ThreadedMessage:
        """Add a new user message (not assigned to thread yet).

        Args:
            content: The message text

        Returns:
            Created message object with unique ID
        """
        self.message_counter += 1
        msg = ThreadedMessage(
            message_id=self.message_counter,
            content=content,
            timestamp=time.time(),
        )
        self.all_messages.append(msg)
        return msg

    def assign_response(self, response: ThreadedResponse) -> None:
        """Assign LLM response to appropriate thread.

        Creates thread if it doesn't exist.

        Args:
            response: The response to assign
        """
        thread_id = response.thread_id

        # Create thread if it doesn't exist
        if thread_id not in self.threads:
            self.threads[thread_id] = ConversationThread(
                thread_id=thread_id,
                topic=response.topic,
            )
            if thread_id >= self.next_thread_id:
                self.next_thread_id = thread_id + 1

        # Add response to thread
        self.threads[thread_id].responses.append(response)
        self.all_responses.append(response)

        # Find and add corresponding message to thread
        msg = next((m for m in self.all_messages if m.message_id == response.message_id), None)
        if msg and msg not in self.threads[thread_id].messages:
            self.threads[thread_id].messages.append(msg)

    def get_thread_context(self, thread_id: int) -> str:
        """Get context for a specific thread.

        Args:
            thread_id: ID of the thread

        Returns:
            Formatted context string for the thread
        """
        if thread_id not in self.threads:
            return ""
        return self.threads[thread_id].get_context()

    def get_all_threads_summary(self) -> str:
        """Get summary of all active threads.

        Returns:
            Formatted summary of threads with topics
        """
        if not self.threads:
            return "No active threads yet."

        summaries = []
        for tid, thread in sorted(self.threads.items()):
            msg_count = len(thread.messages)
            resp_count = len(thread.responses)
            summaries.append(f"Thread {tid}: {thread.topic} ({msg_count} messages, {resp_count} responses)")
        return "\n".join(summaries)


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


# ================================
# System Prompt
# ================================

SYSTEM_PROMPT = """You are a multi-threaded conversation manager.

## YOUR ROLE:
Process user messages sequentially and assign them to conversation threads based on semantic analysis.

## THREAD MANAGEMENT RULES:

### Thread Assignment:
- RELATED messages stay in the SAME thread
- UNRELATED messages get NEW thread IDs (increment from highest existing)
- Use semantic similarity to detect relationships
- Examples:
  * "write an essay on AI" → thread_id=1 (new topic)
  * "tell me a joke" → thread_id=2 (unrelated to AI, new thread)
  * "make that joke funnier" → thread_id=2 (related to jokes, same thread)
  * "what about neural networks in the essay?" → thread_id=1 (related to AI, same thread)

### Response Format:
ALWAYS wrap responses in answer blocks with fence syntax (!!start/!!end):

!!start
---
id: answer_001
block_type: answer
thread_id: 1
message_id: 1
topic: "AI Essay"
reasoning: "New topic about artificial intelligence, creating new thread"
---
[Your response content here - can be multiple paragraphs]
!!end

### Decision Process:
1. Analyze new message: is it related to any existing thread?
2. Check semantic similarity with thread topics
3. If similar (clearly related) → use existing thread_id
4. If not similar (new topic) → create new thread_id
5. Include reasoning field explaining your decision

## IMPORTANT:
- Process messages in order (message_id sequence)
- ONE block per message
- ALWAYS include all metadata fields
- Be smart about semantic similarity (don't create unnecessary threads)
"""


# ================================
# Sequential Message Processor
# ================================


class SequentialMessageProcessor:
    """Process messages sequentially with single LLM."""

    def __init__(
        self,
        stream_controller: SimpleStreamController,
        thread_manager: ThreadManager,
        processor: StreamBlockProcessor,
    ) -> None:
        """Initialize the message processor.

        Args:
            stream_controller: Controller for LLM streaming
            thread_manager: Manager for threads
            processor: StreamBlocks processor
        """
        self.stream_controller = stream_controller
        self.thread_manager = thread_manager
        self.processor = processor
        self.message_queue: asyncio.Queue[ThreadedMessage] = asyncio.Queue()
        self.is_processing = False
        self.current_response_text = ""  # Accumulate streaming text

    async def queue_message(self, content: str) -> ThreadedMessage:
        """Queue a new user message for processing.

        Args:
            content: Message text

        Returns:
            Created message object
        """
        msg = self.thread_manager.add_user_message(content)
        await self.message_queue.put(msg)
        return msg

    def _build_prompt(self, msg: ThreadedMessage) -> str:
        """Build prompt for thread routing.

        Args:
            msg: Message to process

        Returns:
            Formatted prompt with context
        """
        thread_summary = self.thread_manager.get_all_threads_summary()

        return f"""{SYSTEM_PROMPT}

===== CURRENT STATE =====
{thread_summary}

===== NEW MESSAGE =====
Message ID: {msg.message_id}
Content: {msg.content}

===== YOUR TASK =====
Analyze this message and:
1. Determine if it relates to an existing thread (check topics above)
2. Assign appropriate thread_id
3. Respond with threaded_answer block including reasoning

Remember: Use existing thread_id if related, create new thread_id={self.thread_manager.next_thread_id} if not.
"""

    async def process_next_message(self, block_callback: Any, text_callback: Any | None = None) -> None:
        """Process the next message in the queue.

        Args:
            block_callback: Callback to update UI with complete blocks
            text_callback: Optional callback for streaming text updates
        """
        if self.message_queue.empty():
            return

        msg = await self.message_queue.get()
        self.is_processing = True
        self.current_response_text = ""

        try:
            # Build prompt
            prompt = self._build_prompt(msg)

            # Debug: Log that we're starting to stream
            print(f"🔄 Starting LLM stream for message {msg.message_id}")

            # Notify callback that streaming is starting
            if text_callback:
                await text_callback(msg, "[dim green]<<< ASSISTANT STREAMING >>>[/dim green]\n")

            # Stream and extract blocks
            async for event in self.processor.process_stream(self.stream_controller.stream(prompt)):
                # Handle real-time text streaming for better UX
                if isinstance(event, TextDeltaEvent):
                    self.current_response_text += event.delta
                    # Show real-time streaming text if callback provided
                    if text_callback:
                        await text_callback(msg, event.delta)

                elif isinstance(event, BlockExtractedEvent):
                    block = event.block
                    if hasattr(block.metadata, "block_type") and block.metadata.block_type == "answer":
                        # Extract thread routing
                        response = ThreadedResponse(
                            response_id=block.metadata.id,
                            thread_id=block.metadata.thread_id,
                            message_id=block.metadata.message_id,
                            topic=block.metadata.topic,
                            content=block.content.raw_content,
                            reasoning=block.metadata.reasoning,
                            timestamp=time.time(),
                        )

                        # Assign to thread
                        self.thread_manager.assign_response(response)

                        # Update UI
                        await block_callback(msg, response)

        except Exception as e:
            # Log error to console for debugging
            print(f"❌ Error processing message {msg.message_id}: {e}")
            import traceback

            traceback.print_exc()
            raise  # Re-raise so caller can handle it
        finally:
            self.is_processing = False
            self.message_queue.task_done()


# ================================
# Textual UI
# ================================


class MultiThreadedChatApp(App[None]):
    """Multi-threaded chat interface with tabbed views."""

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

    #user-input {
        dock: bottom;
        margin: 0 1 1 1;
        border: solid $accent;
    }

    TabbedContent {
        height: 1fr;
    }

    TabPane {
        padding: 0;
    }

    VerticalScroll {
        height: 100%;
    }

    RichLog {
        height: 100%;
        background: $surface;
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

        # Components
        self.thread_manager = ThreadManager()
        self.stream_controller = SimpleStreamController(api_key)

        # Register Answer block with fence syntax
        syntax = DelimiterFrontmatterSyntax(start_delimiter="!!start", end_delimiter="!!end")
        registry = Registry(syntax=syntax)
        registry.register("answer", Answer)
        self.processor = StreamBlockProcessor(registry)

        self.message_processor = SequentialMessageProcessor(self.stream_controller, self.thread_manager, self.processor)

        self.current_worker: Worker[None] | None = None

    def compose(self) -> ComposeResult:
        """Compose the UI layout."""
        yield Header()
        yield Static("Multi-Threaded Chat - Type messages below", id="status")

        # Tabbed content with multiple tabs
        with TabbedContent(id="thread-tabs"):
            # Tab 1: All Messages (boxed messages)
            with TabPane("All Messages", id="tab-all"):
                yield VerticalScroll(RichLog(id="log-all", highlight=True, markup=True, wrap=True))

            # Tab 2: Raw LLM Output (unprocessed stream)
            with TabPane("Raw LLM Output", id="tab-raw"):
                yield VerticalScroll(RichLog(id="log-raw", highlight=True, markup=True, wrap=True))

        yield Input(placeholder="Type your message and press Enter...", id="user-input")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the app on mount."""
        # Focus the input field
        self.query_one("#user-input", Input).focus()

        # Show welcome message
        all_log = self.query_one("#log-all", RichLog)
        all_log.write("[bold cyan]Multi-Threaded Chat with Single LLM[/bold cyan]")
        all_log.write("[dim]Type messages - LLM will auto-route to appropriate threads[/dim]")
        all_log.write("[dim]Switch tabs to see filtered thread views[/dim]")
        all_log.write("[dim]Press q or Ctrl+C to quit[/dim]\n")

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

        # Queue message
        msg = await self.message_processor.queue_message(message)

        # Display in "All Messages" tab (boxed)
        all_log = self.query_one("#log-all", RichLog)
        user_panel = Panel(message, title=f"[cyan]You[/] (msg#{msg.message_id})", border_style="cyan", box=box.ROUNDED)
        all_log.write(user_panel, scroll_end=True)

        # Display in "Raw LLM Output" tab (plain text)
        raw_log = self.query_one("#log-raw", RichLog)
        raw_log.write(f"[dim cyan]>>> USER (msg#{msg.message_id}):[/dim cyan]\n{message}\n\n", scroll_end=True)

        # Debug logging
        print(f"📨 Queued message {msg.message_id}: {message[:50]}...")

        # If not already processing, start processing
        if not self.message_processor.is_processing:
            print("🚀 Starting worker to process messages")
            self.current_worker = self.run_worker(self.process_messages(), exclusive=False)
        else:
            print("⏳ Already processing, message will be handled when current one completes")

    async def process_messages(self) -> None:
        """Process queued messages."""
        try:
            while not self.message_processor.message_queue.empty():
                await self.message_processor.process_next_message(self.handle_response, self.handle_streaming_text)
        except Exception as e:
            # Display error in UI
            all_log = self.query_one("#log-all", RichLog)
            all_log.write(f"[red]❌ Error: {e}[/red]\n")
            # Error already logged to console by process_next_message

    async def handle_streaming_text(self, msg: ThreadedMessage, text_delta: str) -> None:
        """Handle streaming text updates in real-time.

        Args:
            msg: Original message being responded to
            text_delta: New text chunk to display
        """
        # Display ONLY in "Raw LLM Output" tab (not in All Messages)
        raw_log = self.query_one("#log-raw", RichLog)
        raw_log.write(text_delta, scroll_end=True)

    async def handle_response(self, msg: ThreadedMessage, response: ThreadedResponse) -> None:
        """Handle a response from the LLM.

        Args:
            msg: Original message
            response: LLM response with thread assignment
        """
        thread_id = response.thread_id
        topic = response.topic

        # Update "All Messages" tab with boxed assistant response
        all_log = self.query_one("#log-all", RichLog)
        assistant_panel = Panel(
            response.content,
            title=f"[green]Assistant[/] - Thread {thread_id}: {topic}",
            subtitle=f"[dim]{response.reasoning}[/dim]",
            border_style="green",
            box=box.ROUNDED,
        )
        all_log.write(assistant_panel, scroll_end=True)

        # Update "Raw LLM Output" tab with marker
        raw_log = self.query_one("#log-raw", RichLog)
        raw_log.write(f"\n[dim green]<<< BLOCK EXTRACTED: Thread {thread_id} >>>[/dim green]\n\n", scroll_end=True)

        # Create thread tab if it doesn't exist
        tabs = self.query_one("#thread-tabs", TabbedContent)
        tab_id = f"tab-thread-{thread_id}"

        if not tabs.query(f"#{tab_id}"):
            # Create new tab for this thread
            tab_pane = TabPane(f"Thread {thread_id}: {topic[:20]}", id=tab_id)
            scroll = VerticalScroll(RichLog(id=f"log-thread-{thread_id}", highlight=True, markup=True, wrap=True))
            tab_pane.compose_add_child(scroll)
            await tabs.add_pane(tab_pane)

        # Update thread-specific tab with boxed messages
        thread_log = self.query_one(f"#log-thread-{thread_id}", RichLog)

        # Clear and rebuild thread log with all messages in boxes
        # (In production, would track what's displayed to avoid rebuilding)
        thread = self.thread_manager.threads[thread_id]

        # Show user messages in boxes
        for thread_msg in thread.messages:
            user_panel = Panel(
                thread_msg.content,
                title=f"[cyan]You[/] (msg#{thread_msg.message_id})",
                border_style="cyan",
                box=box.ROUNDED,
            )
            thread_log.write(user_panel, scroll_end=True)

        # Show assistant response in box
        assistant_panel = Panel(response.content, title="[green]Assistant[/]", border_style="green", box=box.ROUNDED)
        thread_log.write(assistant_panel, scroll_end=True)


async def main() -> None:
    """Run the multi-threaded chat interface."""
    # Check API key
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ Error: Set GOOGLE_API_KEY or GEMINI_API_KEY")
        print("Get your key at: https://aistudio.google.com/apikey")
        return

    # Run the app
    app = MultiThreadedChatApp(api_key)
    await app.run_async()


if __name__ == "__main__":
    asyncio.run(main())
