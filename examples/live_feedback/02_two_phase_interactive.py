#!/usr/bin/env python3
"""
Live Feedback Example with Stream Adapters and Pause/Resume

This example demonstrates StreamBlocks' complete interactive workflow system:

1. **Adapter Integration**: Gemini chunks auto-detected and processed by adapter
2. **Two-Phase Workflow**:
   - Phase 1: Discussion questions (yesno, choice, input blocks)
   - Phase 2: Per-operation confirmations (confirm blocks with callbacks)
3. **Stream Pause/Resume**: Stream pauses for user input and resumes with feedback
4. **Native Chunks**: Access to original Gemini chunks with metadata
5. **Event-Driven**: Rich event types (RawTextEvent, BlockExtractedEvent, etc.)

Key Features:
- EVERY file operation (create, edit, delete) triggers its own confirmation
- Interactive questions before operations begin
- Questionary-based CLI for beautiful user experience
- Full conversation context management
- Multiple pause/resume cycles

This showcases StreamBlocks' adapter system and ability to create
interactive, stateful LLM applications with fine-grained control.
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import TYPE_CHECKING

import questionary
from google import genai  # type: ignore[import-not-found]
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from hother.streamblocks import (
    BlockDeltaEvent,
    BlockExtractedEvent,
    BlockRejectedEvent,
    DelimiterFrontmatterSyntax,
    RawTextEvent,
    Registry,
    StreamBlockProcessor,
)
from hother.streamblocks.blocks.files import (
    FileContent,
    FileContentContent,
    FileContentMetadata,
    FileOperations,
    FileOperationsContent,
    FileOperationsMetadata,
)
from hother.streamblocks.blocks.interactive import (
    Choice,
    ChoiceContent,
    ChoiceMetadata,
    Confirm,
    ConfirmContent,
    ConfirmMetadata,
    Input,
    InputContent,
    InputMetadata,
    YesNo,
    YesNoContent,
    YesNoMetadata,
)
from hother.streamblocks.blocks.message import Message, MessageContent, MessageMetadata
from hother.streamblocks.core.models import ExtractedBlock

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable

    from hother.streamblocks.core.types import BaseContent, BaseMetadata

# Create Rich console for beautiful output
console = Console()


class PausableGeminiStream:
    """Controllable Gemini stream that can be paused and resumed with conversation updates.

    This class wraps the Gemini API to provide pause/resume capabilities and conversation
    state management. It uses asyncio primitives to coordinate between the stream consumer
    and the LLM generation.
    """

    def __init__(self, api_key: str, model_id: str = "gemini-2.5-flash") -> None:
        """Initialize the pausable stream.

        Args:
            api_key: Google API key for Gemini
            model_id: Model identifier to use
        """
        self.client = genai.Client(api_key=api_key)  # type: ignore[attr-defined]
        self.model_id = model_id
        self.conversation_history: list[dict[str, str]] = []
        self._pause_event = asyncio.Event()
        self._resume_event = asyncio.Event()
        self._stop_event = asyncio.Event()
        self._user_feedback: str | None = None

        # Start in streaming mode (not paused)
        self._pause_event.clear()
        self._resume_event.clear()

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation history.

        Args:
            role: Message role (user, assistant, system)
            content: Message content
        """
        self.conversation_history.append({"role": role, "content": content})

    def pause_and_wait_for_feedback(self, feedback: str) -> None:
        """Pause the stream and queue user feedback for the next generation.

        Args:
            feedback: User feedback to insert into conversation
        """
        self._user_feedback = feedback
        self._pause_event.set()
        self._resume_event.clear()

    def resume(self) -> None:
        """Resume stream generation."""
        self._resume_event.set()

    def stop(self) -> None:
        """Stop the stream completely."""
        self._stop_event.set()

    async def stream(self, initial_prompt: str, system_prompt: str) -> AsyncIterator:  # type: ignore[type-arg]
        """Stream from Gemini with pause/resume support.

        This generator yields Gemini chunks (not text strings) which are then
        processed by StreamBlocks adapter system. The adapter handles text extraction.
        The stream can be paused mid-generation and restarted with updated context.

        Args:
            initial_prompt: Initial user prompt
            system_prompt: System prompt defining AI behavior

        Yields:
            Gemini chunk objects (adapter extracts text automatically)
        """
        # Initialize conversation with system prompt and initial user message
        if not self.conversation_history:
            self.add_message("user", f"{system_prompt}\n\n{initial_prompt}")

        while not self._stop_event.is_set():
            # Build the full conversation context
            full_context = "\n\n".join([f"{msg['role']}: {msg['content']}" for msg in self.conversation_history])

            try:
                # Stream the response
                response = await self.client.aio.models.generate_content_stream(  # type: ignore[attr-defined]
                    model=self.model_id,
                    contents=full_context,
                )

                accumulated_response: str = ""
                async for chunk in response:  # type: ignore[var-annotated]
                    # Check if we need to pause
                    if self._pause_event.is_set():
                        # Save what we've generated so far
                        if accumulated_response:
                            self.add_message("assistant", accumulated_response)

                        # Add user feedback to conversation
                        if self._user_feedback:
                            self.add_message("user", self._user_feedback)
                            self._user_feedback = None

                        # Clear pause and wait for resume
                        self._pause_event.clear()
                        await self._resume_event.wait()

                        # Break to restart generation with updated context
                        break

                    # Extract text for conversation history (adapter will also extract for processing)
                    if chunk.text:  # type: ignore[attr-defined]
                        text: str = str(chunk.text)  # type: ignore[attr-defined]
                        accumulated_response += text

                    # Yield original Gemini chunk (not text string)
                    # The StreamBlocks adapter will extract text automatically
                    yield chunk
                else:
                    # Stream completed naturally (no pause)
                    if accumulated_response:
                        self.add_message("assistant", accumulated_response)
                        # Continue the outer loop to allow more confirmations
                        # The AI should generate more confirmation blocks for subsequent operations
                    else:
                        # Empty response means conversation is truly complete
                        break

            except Exception as e:
                print(f"\n❌ Error during streaming: {e}")
                break


class BlockCallbackRegistry:
    """Registry for associating block types with validation callbacks.

    This demonstrates Type 2 pause/resume: callback-based processing where
    specific block types trigger registered validation functions.
    """

    def __init__(self) -> None:
        """Initialize an empty callback registry."""
        self._callbacks: dict[str, Callable[[ExtractedBlock], tuple[bool, str]]] = {}

    def register(self, block_type: str, callback: Callable[[ExtractedBlock], tuple[bool, str]]) -> None:
        """Register a callback function for a block type.

        Args:
            block_type: The block type to associate with this callback
            callback: Function that takes an ExtractedBlock and returns (approved, feedback)
        """
        self._callbacks[block_type] = callback

    def get(self, block_type: str) -> Callable[[ExtractedBlock], tuple[bool, str]] | None:
        """Get the callback function for a block type.

        Args:
            block_type: The block type to look up

        Returns:
            The registered callback function, or None if not found
        """
        return self._callbacks.get(block_type)


def create_system_prompt() -> str:
    """Create the system prompt instructing the AI to use two-phase interactive workflow."""
    return """You are an expert software architect helping with system refactoring.

## CRITICAL BLOCK FORMATTING RULES

1. **Content section MUST be valid YAML** - no prose, no explanations inside blocks
2. **Always separate blocks from text** - put a blank line before and after each block
3. **Never combine blocks** - emit ONE block at a time, then STOP
4. **After emitting a block, STOP generating** - wait for user response
5. **Prose goes in MESSAGE blocks or RAW TEXT** - never in YAML content sections

## TWO-PHASE INTERACTIVE WORKFLOW

Your workflow has TWO distinct phases:

### PHASE 1: DISCUSSION & REQUIREMENTS (TYPE 1 Pause/Resume)
Before starting any operations, you MUST:
1. Ask ONE clarifying question using ONE interactive block
2. STOP and wait for user response
3. After receiving response, ask the next question
4. Repeat until you have 2-3 answers total
5. Use the answers to refine your approach

### PHASE 2: OPERATION EXECUTION (TYPE 2 Pause/Resume)
After gathering requirements, for EVERY file operation you MUST:
1. Emit ONE confirmation block for that SINGLE operation
2. STOP and wait for user approval
3. Only proceed after receiving user feedback
4. Process ONE operation at a time in sequence

## Block Formats

**IMPORTANT**: The content section (after the second `---`) must contain ONLY valid YAML.
NO prose, NO explanations, NO extra text. Just YAML fields.

### PHASE 1: Interactive Question Blocks (Asked FIRST)

**CORRECT EXAMPLE** - Yes/No Question:
!!start
---
id: question_001
block_type: yesno
yes_label: "Yes"
no_label: "No"
---
prompt: "Do you want to include comprehensive tests for the OAuth2 implementation?"
!!end

**INCORRECT** - Don't do this:
!!start
---
id: question_001
block_type: yesno
---
prompt: "Do you want tests?"
Okay, my next question is about...  ❌ WRONG - prose in content section
!!end

Also INCORRECT - Don't do this:
!!endNow let me ask another question...  ❌ WRONG - no separation after block

**CORRECT EXAMPLE** - Single Choice Question:
!!start
---
id: question_002
block_type: choice
display_style: "radio"
---
prompt: "Which authentication approach do you prefer?"
options:
  - JWT with refresh tokens
  - JWT with short-lived tokens only
  - OAuth2 with external provider
!!end

**CORRECT EXAMPLE** - Text Input Question:
!!start
---
id: question_003
block_type: input
input_type: "text"
---
prompt: "Are there any specific OAuth2 providers or requirements I should know about?"
placeholder: "e.g., Google OAuth, custom scopes, etc."
default_value: ""
!!end

**WORKFLOW**: Emit ONE question block, then STOP. Wait for response. Then emit next question.

### PHASE 2: Confirmation and Operation Blocks (Used AFTER questions)

### 1. Confirmation Block (REQUIRED before EVERY file operation)

Example for CREATING a file:
!!start
---
id: confirm_create_001
block_type: confirm
confirm_label: "Yes, Create"
cancel_label: "Cancel"
danger_mode: false
---
prompt: "📝 File Creation Confirmation"
message: |
  I want to CREATE the following file:
  - src/auth/oauth2.py

  This file will contain:
  - OAuth2 authentication handler
  - Token validation logic
  - User authentication methods

  Do you approve creating this file?
!!end

Example for DELETING a file:
!!start
---
id: confirm_delete_001
block_type: confirm
confirm_label: "Yes, Delete"
cancel_label: "Cancel"
danger_mode: true
---
prompt: "⚠️ File Deletion Confirmation"
message: |
  I want to DELETE the following file:
  - src/legacy/auth.py

  WARNING: This file is currently in use by the production system.
  Deletion is IRREVERSIBLE.

  Do you approve deleting this file?
!!end

Example for EDITING/WRITING file content:
!!start
---
id: confirm_write_001
block_type: confirm
confirm_label: "Yes, Write"
cancel_label: "Cancel"
danger_mode: false
---
prompt: "✏️ File Write Confirmation"
message: |
  I want to WRITE content to:
  - src/auth/oauth2.py

  The file will contain approximately 50 lines including:
  - OAuth2Handler class
  - Token authentication methods
  - Error handling

  Do you approve writing this content?
!!end

### 2. File Operations Block
For listing files to create or delete:
!!start
---
id: files_001
block_type: files_operations
description: Creating new OAuth2 authentication system
---
src/auth/oauth2.py:C
src/auth/token_manager.py:C
src/auth/user_service.py:C
tests/test_oauth2.py:C
!!end

Where: C=Create, D=Delete

### 3. File Content Block
For writing complete file contents:
!!start
---
id: file_001
block_type: file_content
file: src/auth/oauth2.py
description: OAuth2 authentication implementation
---
from typing import Optional
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

class OAuth2Handler:
    \"\"\"Handles OAuth2 authentication flow.\"\"\"

    def __init__(self):
        self.oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

    async def authenticate(self, token: str) -> dict:
        \"\"\"Authenticate user from token.\"\"\"
        # Implementation here
        pass
!!end

### 4. Message Block
For explanations and status updates:
!!start
---
id: msg_001
block_type: message
message_type: info
title: "Migration Plan Overview"
---
I'll help you migrate from the legacy auth system to OAuth2. This is a multi-step process
that requires careful coordination to avoid breaking the production system.
!!end

## IMPORTANT RULES:

### Phase 1 Rules (Discussion):
1. ALWAYS start by asking 2-3 clarifying questions using yesno, choice, or input blocks
2. WAIT for user responses after each question
3. Use the gathered information to refine your approach
4. NEVER skip the discussion phase

### Phase 2 Rules (Operations):
1. ALWAYS emit a confirmation block BEFORE EVERY SINGLE file operation (create, edit, delete, write)
2. Process ONE operation at a time - NEVER batch multiple operations
3. After EACH confirmation block, STOP generating and wait for user response
4. Only proceed to the NEXT operation after receiving confirmation for the CURRENT one
5. Use message blocks to explain your overall approach BEFORE starting operations
6. Break complex tasks into clear, individual steps

## COMPLETE WORKFLOW:

### Phase 1 (Discussion):
1. Use a message block to acknowledge the task
2. Emit ONE yesno/choice/input block with your first question
3. **STOP GENERATING** - wait for user response
4. After receiving response, emit ONE block with your next question
5. **STOP GENERATING** - wait for user response
6. After receiving response, emit ONE block with your final question (if needed)
7. **STOP GENERATING** - wait for user response
8. Use a message block to summarize gathered requirements

**KEY**: ONE question block at a time. STOP after each. NO multiple blocks in one response.

### Phase 2 (Operations):
1. Emit ONE confirmation block for the FIRST operation
2. **STOP GENERATING** - wait for user response
3. After receiving approval, emit ONE files_operations or file_content block
4. Emit ONE confirmation block for the NEXT operation
5. **STOP GENERATING** - wait for user response
6. Repeat steps 3-5 until all operations are complete

**KEY**: ONE block at a time. STOP after each confirmation. NO multiple operations in one response.

When you receive user feedback:
- After questions: acknowledge briefly, then emit the next question block
- After confirmations: if approved, proceed with that specific operation; if rejected, suggest alternatives
- Always keep responses focused and structured
"""


# ============================================================================
# TYPE 1: Event-Driven Interactive Question Handlers
# These demonstrate direct event processing - no callbacks involved
# ============================================================================


def display_yesno_question(block: ExtractedBlock[YesNoMetadata, YesNoContent]) -> str:
    """Handle yes/no question using questionary (Type 1: direct processing).

    Args:
        block: The yes/no question block

    Returns:
        Feedback message with user's response
    """
    print("\n" + "=" * 80)
    print("📋 TYPE 1: Discussion Question (Event-Driven)")
    print("=" * 80)

    metadata = block.metadata
    content = block.content

    print(f"\n❓ {content.prompt}")

    # Use questionary for interactive yes/no
    answer = questionary.confirm(
        f"{content.prompt}",
        default=True,
    ).ask()

    response_text = metadata.yes_label if answer else metadata.no_label
    return f"""You asked: "{content.prompt}"

My response: {response_text}

Please continue with the planning based on my answer."""


def display_choice_question(block: ExtractedBlock[ChoiceMetadata, ChoiceContent]) -> str:
    """Handle single choice question using questionary (Type 1: direct processing).

    Args:
        block: The choice question block

    Returns:
        Feedback message with user's selected option
    """
    print("\n" + "=" * 80)
    print("📋 TYPE 1: Discussion Question (Event-Driven)")
    print("=" * 80)

    content = block.content

    print(f"\n🔘 {content.prompt}")

    # Use questionary for single choice
    choice = questionary.select(
        f"{content.prompt}",
        choices=content.options,
    ).ask()

    return f"""You asked: "{content.prompt}"

My selection: {choice}

Please continue with the planning based on my selection."""


def display_input_question(block: ExtractedBlock[InputMetadata, InputContent]) -> str:
    """Handle text input question using questionary (Type 1: direct processing).

    Args:
        block: The input question block

    Returns:
        Feedback message with user's text input
    """
    print("\n" + "=" * 80)
    print("📋 TYPE 1: Discussion Question (Event-Driven)")
    print("=" * 80)

    metadata = block.metadata
    content = block.content

    print(f"\n✏️  {content.prompt}")

    # Prepare validation if pattern is provided
    validate = None
    if metadata.pattern:
        import re

        def validate_pattern(text: str) -> bool | str:
            if not text and metadata.min_length > 0:
                return "This field is required"
            if text and not re.match(metadata.pattern, text):  # type: ignore[arg-type]
                return f"Input must match pattern: {metadata.pattern}"
            if metadata.max_length and len(text) > metadata.max_length:
                return f"Input must be at most {metadata.max_length} characters"
            return True

        validate = validate_pattern

    # Use questionary for text input
    answer = questionary.text(
        f"{content.prompt}",
        default=content.default_value or "",
        validate=validate,
    ).ask()

    return f"""You asked: "{content.prompt}"

My response: {answer}

Please continue with the planning based on my input."""


# ============================================================================
# TYPE 2: Callback-Based Validation Handler
# This demonstrates callback processing - registered in the callback registry
# ============================================================================


def validate_file_operation(block: ExtractedBlock[ConfirmMetadata, ConfirmContent]) -> tuple[bool, str]:
    """Validate file operation using questionary (Type 2: callback processing).

    This is a callback function registered for 'confirm' block types.

    Args:
        block: The confirmation block to validate

    Returns:
        Tuple of (approved, feedback_message)
    """
    print("\n" + "=" * 80)
    print("🔍 TYPE 2: Operation Validation (Callback-Based)")
    print("=" * 80)

    metadata = block.metadata
    content = block.content

    # Display the confirmation details
    print(f"\n⚠️  {content.prompt}")
    print("\n" + "-" * 80)
    print(content.message)
    print("-" * 80)

    # Detect operation type for feedback
    message_lower = content.message.lower()
    is_create = "create" in message_lower
    is_delete = "delete" in message_lower
    is_write = "write" in message_lower

    # Use questionary for selection
    choices = [
        metadata.confirm_label,
        metadata.cancel_label,
        "Approve with modifications",
    ]

    # Apply danger styling if this is a dangerous operation
    style = questionary.Style(
        [
            ("qmark", "fg:red bold" if metadata.danger_mode else "fg:yellow bold"),
            ("question", "bold"),
            ("answer", "fg:green bold" if not metadata.danger_mode else "fg:red bold"),
            ("pointer", "fg:red bold" if metadata.danger_mode else "fg:blue bold"),
            ("highlighted", "fg:red bold" if metadata.danger_mode else "fg:blue bold"),
        ]
    )

    choice = questionary.select(
        "Your decision:",
        choices=choices,
        style=style,
    ).ask()

    if choice == metadata.confirm_label:
        # Approved
        if is_delete:
            feedback = """I approve this deletion. Please proceed with removing this file.
Ensure you have backups before deleting.
After this operation is complete, please ask for confirmation for the next operation."""
        elif is_create:
            feedback = """I approve creating this file. Please proceed with this creation.
After this file is created, please ask for confirmation for the next operation."""
        elif is_write:
            feedback = """I approve writing this content. Please proceed with writing to this file.
After writing is complete, please ask for confirmation for the next operation."""
        else:
            feedback = """I approve this operation. Please proceed.
After this operation is complete, please ask for confirmation for the next operation."""
        return True, feedback

    if choice == metadata.cancel_label:
        # Rejected
        if is_delete:
            feedback = """I do not approve this deletion at this time.
Please skip deleting this file for now and proceed to the next operation.
We can revisit deletions after the new implementation is fully tested."""
        elif is_create:
            feedback = """I do not approve creating this file at this time.
Please skip this file and proceed to the next operation, or suggest an alternative approach."""
        elif is_write:
            feedback = """I do not approve writing this content at this time.
Please skip this file and proceed to the next operation, or suggest alternative content."""
        else:
            feedback = """I do not approve this operation at this time.
Please skip this step and proceed to the next operation, or suggest an alternative approach."""
        return False, feedback

    # Approve with modifications
    modifications = questionary.text(
        "Provide your modifications/instructions:",
        multiline=False,
    ).ask()

    feedback = f"""I approve this operation with the following modifications:

{modifications}

Please apply these changes and proceed with this operation.
After this operation is complete, please ask for confirmation for the next operation."""
    return True, feedback


async def process_with_live_feedback(
    stream: PausableGeminiStream,
    processor: StreamBlockProcessor,
    initial_prompt: str,
    system_prompt: str,
    callback_registry: BlockCallbackRegistry,
) -> None:
    """Process the LLM stream with live feedback capability demonstrating two pause/resume types.

    This function orchestrates the two-phase interactive workflow:

    TYPE 1: Event-Driven Interactive Questions (Discussion Phase)
    - Directly processes yesno, choice, and input blocks
    - No callbacks involved, just event handling
    - Demonstrates pause/resume via direct event processing

    TYPE 2: Callback-Based Validation (Operation Phase)
    - Uses registered callbacks for confirm blocks
    - Demonstrates pause/resume via callback mechanism
    - Shows how blocks can trigger custom validation logic

    Args:
        stream: The pausable Gemini stream
        processor: StreamBlocks processor
        initial_prompt: Initial user prompt
        system_prompt: System instructions
        callback_registry: Registry mapping block types to validation callbacks
    """
    extracted_blocks: list[ExtractedBlock[BaseMetadata, BaseContent]] = []
    discussion_questions_count = 0
    confirmation_count = 0

    # Display task in a Rich panel
    console.print(
        Panel(
            f"[bold cyan]Task:[/bold cyan]\n{initial_prompt}",
            title="🚀 Starting Live Feedback Example",
            border_style="cyan",
            box=box.DOUBLE,
        )
    )

    # Start processing the stream
    # The adapter auto-detects Gemini chunks and extracts text
    async for event in processor.process_stream(stream.stream(initial_prompt, system_prompt)):
        if isinstance(event, RawTextEvent):
            # Display raw text from LLM (text outside of blocks)
            text = event.data.strip()
            if text:
                console.print(Panel(text, title="💬 LLM Response", border_style="dim cyan", box=box.ROUNDED))

        elif isinstance(event, BlockExtractedEvent):
            block = event.block
            extracted_blocks.append(block)
            block_type = block.metadata.block_type

            # Show block extraction with Rich panel
            console.print(
                Panel(
                    f"[bold cyan]Type:[/bold cyan] {block_type}\n[bold cyan]ID:[/bold cyan] {block.metadata.id}",
                    title="✅ Block Extracted",
                    border_style="green",
                    box=box.DOUBLE,
                )
            )

            # Handle different block types
            if block_type == "message":
                if isinstance(block.metadata, MessageMetadata) and isinstance(block.content, MessageContent):
                    metadata = block.metadata
                    content = block.content

                    icons = {
                        "info": "ℹ️",
                        "warning": "⚠️",
                        "error": "❌",
                        "success": "✅",
                        "status": "📊",
                    }
                    icon = icons.get(metadata.message_type, "💬")

                    # Color scheme based on message type
                    colors = {
                        "info": "cyan",
                        "warning": "yellow",
                        "error": "red",
                        "success": "green",
                        "status": "blue",
                    }
                    color = colors.get(metadata.message_type, "white")

                    console.print(
                        Panel(
                            content.raw_content.strip(),
                            title=f"{icon} {metadata.title or 'Message'}",
                            border_style=color,
                            box=box.ROUNDED,
                        )
                    )

            elif block_type == "files_operations":
                if isinstance(block.metadata, FileOperationsMetadata) and isinstance(
                    block.content, FileOperationsContent
                ):
                    metadata = block.metadata
                    content = block.content

                    # Create table for file operations
                    table = Table(
                        title=f"📁 File Operations: {metadata.id}",
                        show_header=True,
                        box=box.ROUNDED,
                        border_style="yellow",
                    )
                    table.add_column("Action", style="cyan bold", width=10)
                    table.add_column("File Path", style="yellow")

                    for op in content.operations:
                        icon = {"create": "✅", "edit": "📝", "delete": "❌"}.get(op.action, "❓")
                        action_text = f"{icon} {op.action.upper()}"
                        table.add_row(action_text, op.path)

                    if metadata.description:
                        console.print(f"[dim italic]{metadata.description}[/dim italic]")

                    console.print(table)

            elif block_type == "file_content":
                if isinstance(block.metadata, FileContentMetadata) and isinstance(block.content, FileContentContent):
                    metadata = block.metadata
                    content = block.content

                    # Detect language from file extension
                    file_ext = metadata.file.split(".")[-1] if "." in metadata.file else "text"
                    lang_map = {
                        "py": "python",
                        "js": "javascript",
                        "ts": "typescript",
                        "rs": "rust",
                        "go": "go",
                        "java": "java",
                        "cpp": "cpp",
                        "c": "c",
                        "sh": "bash",
                        "yaml": "yaml",
                        "yml": "yaml",
                        "json": "json",
                        "md": "markdown",
                    }
                    language = lang_map.get(file_ext, "python")

                    # Show code with syntax highlighting
                    syntax_obj = Syntax(
                        content.raw_content.strip(), language, theme="monokai", line_numbers=True, word_wrap=False
                    )

                    title = f"📄 {metadata.file}"
                    if metadata.description:
                        title += f" - {metadata.description}"

                    console.print(Panel(syntax_obj, title=title, border_style="blue", box=box.ROUNDED))

            # ========================================================================
            # TYPE 1: Event-Driven Interactive Questions (Direct Processing)
            # ========================================================================
            elif block_type == "yesno":
                if isinstance(block.metadata, YesNoMetadata) and isinstance(block.content, YesNoContent):
                    discussion_questions_count += 1

                    # Direct event processing - no callback
                    feedback = display_yesno_question(
                        ExtractedBlock[YesNoMetadata, YesNoContent](
                            metadata=block.metadata,
                            content=block.content,
                            syntax_name=block.syntax_name,
                            raw_text=block.raw_text,
                            line_start=block.line_start,
                            line_end=block.line_end,
                            hash_id=block.hash_id,
                        )
                    )

                    print("\n📝 Inserting response into conversation...")
                    stream.pause_and_wait_for_feedback(feedback)

                    print("▶️  Resuming stream with user response...\n")
                    print("=" * 80)

                    stream.resume()

            elif block_type == "choice":
                if isinstance(block.metadata, ChoiceMetadata) and isinstance(block.content, ChoiceContent):
                    discussion_questions_count += 1

                    # Direct event processing - no callback
                    feedback = display_choice_question(
                        ExtractedBlock[ChoiceMetadata, ChoiceContent](
                            metadata=block.metadata,
                            content=block.content,
                            syntax_name=block.syntax_name,
                            raw_text=block.raw_text,
                            line_start=block.line_start,
                            line_end=block.line_end,
                            hash_id=block.hash_id,
                        )
                    )

                    print("\n📝 Inserting selection into conversation...")
                    stream.pause_and_wait_for_feedback(feedback)

                    print("▶️  Resuming stream with user selection...\n")
                    print("=" * 80)

                    stream.resume()

            elif block_type == "input":
                if isinstance(block.metadata, InputMetadata) and isinstance(block.content, InputContent):
                    discussion_questions_count += 1

                    # Direct event processing - no callback
                    feedback = display_input_question(
                        ExtractedBlock[InputMetadata, InputContent](
                            metadata=block.metadata,
                            content=block.content,
                            syntax_name=block.syntax_name,
                            raw_text=block.raw_text,
                            line_start=block.line_start,
                            line_end=block.line_end,
                            hash_id=block.hash_id,
                        )
                    )

                    print("\n📝 Inserting input into conversation...")
                    stream.pause_and_wait_for_feedback(feedback)

                    print("▶️  Resuming stream with user input...\n")
                    print("=" * 80)

                    stream.resume()

            # ========================================================================
            # TYPE 2: Callback-Based Validation (Callback Processing)
            # ========================================================================
            elif callback := callback_registry.get(block_type):
                # Check if this is a confirm block (expected for Type 2)
                if (
                    block_type == "confirm"
                    and isinstance(block.metadata, ConfirmMetadata)
                    and isinstance(block.content, ConfirmContent)
                ):
                    confirmation_count += 1

                    # Callback-based processing
                    approved, feedback = callback(
                        ExtractedBlock[ConfirmMetadata, ConfirmContent](
                            metadata=block.metadata,
                            content=block.content,
                            syntax_name=block.syntax_name,
                            raw_text=block.raw_text,
                            line_start=block.line_start,
                            line_end=block.line_end,
                            hash_id=block.hash_id,
                        )
                    )

                    print(f"\n{'✅' if approved else '❌'} User decision: {'APPROVED' if approved else 'REJECTED'}")
                    print("📝 Inserting feedback into conversation...")

                    # Pause the stream and inject feedback
                    stream.pause_and_wait_for_feedback(feedback)

                    print("▶️  Resuming stream with user feedback...\n")
                    print("=" * 80)

                    # Resume the stream
                    stream.resume()

        elif isinstance(event, BlockDeltaEvent):
            # Show progress indicator for blocks being parsed (subtle)
            console.print("[dim].[/dim]", end="")

        elif isinstance(event, BlockRejectedEvent):
            # Block failed validation
            console.print(
                Panel(
                    f"[bold red]Reason:[/bold red] {event.reason}",
                    title="⚠️ Block Rejected",
                    border_style="red",
                    box=box.ROUNDED,
                )
            )

    # Summary with Rich
    console.print("\n")
    console.print(
        Panel("[bold cyan]Execution Complete[/bold cyan]", title="📊 Summary", border_style="green", box=box.DOUBLE)
    )

    # Main stats table
    summary_table = Table(title="Statistics", box=box.HEAVY, border_style="cyan")
    summary_table.add_column("Metric", style="cyan bold")
    summary_table.add_column("Count", style="green bold", justify="right")

    summary_table.add_row("Total Blocks", str(len(extracted_blocks)))
    summary_table.add_row("TYPE 1 (Discussion)", str(discussion_questions_count))
    summary_table.add_row("TYPE 2 (Validation)", str(confirmation_count))

    console.print(summary_table)

    # Count by type
    block_counts: dict[str, int] = {}
    for block in extracted_blocks:
        bt = block.metadata.block_type
        block_counts[bt] = block_counts.get(bt, 0) + 1

    # Blocks by type table
    if block_counts:
        type_table = Table(title="Blocks by Type", box=box.ROUNDED, border_style="yellow")
        type_table.add_column("Block Type", style="yellow bold")
        type_table.add_column("Count", style="cyan bold", justify="right")

        for bt, count in sorted(block_counts.items()):
            type_table.add_row(bt, str(count))

        console.print(type_table)

    console.print("\n[bold green]✅ Example completed![/bold green]")


async def main() -> None:
    """Run the live feedback example with two types of pause/resume."""
    # Introduction with Rich panel
    console.print(
        Panel(
            "[bold cyan]StreamBlocks Live Feedback Example[/bold cyan]\n"
            "[bold yellow]Two Pause/Resume Types[/bold yellow]",
            title="🎯 Welcome",
            border_style="cyan",
            box=box.DOUBLE,
        )
    )

    # Description of pause/resume patterns
    description = """[bold]This example demonstrates TWO distinct pause/resume patterns:[/bold]

[bold cyan]📋 TYPE 1: Event-Driven Interactive Questions (Discussion Phase)[/bold cyan]
  • LLM asks clarifying questions at the beginning
  • Questions processed directly in the event loop
  • Uses yesno, choice, and input blocks
  • No callbacks involved - pure event processing

[bold yellow]🔍 TYPE 2: Callback-Based Validation (Operation Phase)[/bold yellow]
  • LLM requests approval for each file operation
  • Confirmations processed via registered callbacks
  • Uses confirm blocks with validation logic
  • Demonstrates callback mechanism pattern

[bold green]✨ Both types use questionary for beautiful interactive CLI[/bold green]
"""
    console.print(Panel(description, border_style="dim cyan", box=box.ROUNDED))

    # Check for API key
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        console.print(
            Panel(
                "[bold red]Error:[/bold red] Please set GOOGLE_API_KEY or GEMINI_API_KEY environment variable",
                title="❌ Missing API Key",
                border_style="red",
                box=box.HEAVY,
            )
        )
        return

    # Create the pausable stream
    stream = PausableGeminiStream(api_key)

    # Create system prompt
    system_prompt = create_system_prompt()

    # Create syntax and registry
    syntax = DelimiterFrontmatterSyntax(
        start_delimiter="!!start",
        end_delimiter="!!end",
    )

    registry = Registry(syntax=syntax)

    # Register Type 1 blocks (Discussion Questions - Event-Driven)
    registry.register("yesno", YesNo)
    registry.register("choice", Choice)
    registry.register("input", Input)

    # Register Type 2 blocks (Operation Validation - Callback-Based)
    registry.register("confirm", Confirm)

    # Register other blocks
    registry.register("files_operations", FileOperations)
    registry.register("file_content", FileContent)
    registry.register("message", Message)

    # Create callback registry and register Type 2 validation callback
    callback_registry = BlockCallbackRegistry()
    callback_registry.register("confirm", validate_file_operation)

    # Create processor with adapter auto-detection
    # The processor will automatically detect Gemini chunks and use GeminiAdapter
    processor = StreamBlockProcessor(
        registry,
        lines_buffer=10,
        # Adapter configuration (defaults shown):
        # emit_original_events=True,   # Pass through native Gemini chunks
        # emit_text_deltas=True,        # Real-time text streaming (disabled for line-based processing)
        # auto_detect_adapter=True,     # Auto-detect chunk type from first chunk
    )

    # The realistic task
    task = """I need to refactor our legacy authentication system to use OAuth2.

The current system has:
- Legacy password-based auth in src/legacy/auth.py
- Session management in src/legacy/session_manager.py
- User models in src/legacy/user_model.py

Please help me migrate to OAuth2 with JWT tokens.

IMPORTANT: This is a production system, so I need you to:

PHASE 1 - DISCUSSION (ask me questions FIRST):
1. Ask me clarifying questions about the requirements
2. Understand my preferences and constraints
3. Wait for my responses before proceeding

PHASE 2 - OPERATIONS (after discussion):
1. Explain your migration approach
2. Ask for my confirmation BEFORE EACH file operation (creating, editing, deleting)
3. Process ONE file at a time - wait for my approval before proceeding to the next
4. Create the new OAuth2 implementation step-by-step
5. Provide tests for the new system

I want to answer your questions first, then review and approve EVERY operation individually.
Safety and clarity are critical - no rushing or batch operations."""

    # Process with live feedback (demonstrating both pause/resume types)
    await process_with_live_feedback(stream, processor, task, system_prompt, callback_registry)


if __name__ == "__main__":
    asyncio.run(main())
