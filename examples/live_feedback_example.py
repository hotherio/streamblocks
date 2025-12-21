#!/usr/bin/env python3
"""
Live Feedback Example with Stream Pause/Resume and Per-Operation Confirmations

This example demonstrates a realistic scenario where:
1. An LLM streams a response for refactoring a critical system
2. A confirmation block is extracted for EACH file operation requiring user approval
3. The stream is paused to wait for user confirmation
4. User feedback is inserted into the conversation
5. The stream is resumed with the updated context
6. Steps 2-5 repeat for every individual operation

The key feature: EVERY file operation (create, edit, delete) triggers its own confirmation,
creating a truly interactive, step-by-step workflow with multiple pause/resume cycles.

This showcases StreamBlocks' ability to create interactive, stateful LLM applications
with fine-grained control over the generation process.
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import TYPE_CHECKING

from google import genai  # type: ignore[import-not-found]

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hother.streamblocks import (
    DelimiterFrontmatterSyntax,
    EventType,
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
from hother.streamblocks.blocks.interactive import Confirm, ConfirmContent, ConfirmMetadata
from hother.streamblocks.blocks.message import Message, MessageContent, MessageMetadata
from hother.streamblocks.core.models import ExtractedBlock

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from hother.streamblocks.core.types import BaseContent, BaseMetadata


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

    async def stream(self, initial_prompt: str, system_prompt: str) -> AsyncIterator[str]:
        """Stream from Gemini with pause/resume support.

        This generator yields text chunks and can be paused mid-stream. When paused,
        it will restart the generation with updated conversation context.

        Args:
            initial_prompt: Initial user prompt
            system_prompt: System prompt defining AI behavior

        Yields:
            Text chunks from the LLM
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

                    if chunk.text:  # type: ignore[attr-defined]
                        text: str = str(chunk.text)  # type: ignore[attr-defined]
                        accumulated_response += text
                        yield text
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


def create_system_prompt() -> str:
    """Create the system prompt instructing the AI to use confirmation blocks."""
    return """You are an expert software architect helping with system refactoring.

CRITICAL WORKFLOW RULE: For EVERY file operation (create, edit, delete, or write), you MUST:
1. Emit a confirmation block for that SINGLE operation
2. STOP and wait for user approval
3. Only proceed after receiving user feedback
4. Process ONE operation at a time in sequence

## Block Formats

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
1. ALWAYS emit a confirmation block BEFORE EVERY SINGLE file operation (create, edit, delete, write)
2. Process ONE operation at a time - NEVER batch multiple operations
3. After EACH confirmation block, STOP generating and wait for user response
4. Only proceed to the NEXT operation after receiving confirmation for the CURRENT one
5. Use message blocks to explain your overall approach BEFORE starting operations
6. Break complex tasks into clear, individual steps

## STEP-BY-STEP WORKFLOW:
1. Use a message block to explain your plan
2. Emit confirmation for the FIRST operation
3. WAIT for user response
4. Process user feedback and adjust if needed
5. Proceed with that ONE operation (files_operations or file_content block)
6. Emit confirmation for the NEXT operation
7. Repeat steps 3-6 until all operations are complete

When you receive user feedback after a confirmation:
- If approved: proceed with ONLY that specific operation, then ask for confirmation for the next
- If rejected: suggest alternatives or modifications, but still proceed one operation at a time
- Always acknowledge the user's decision before continuing
"""


def display_confirmation(block: ExtractedBlock[ConfirmMetadata, ConfirmContent]) -> tuple[bool, str]:
    """Display confirmation dialog and get user response.

    Args:
        block: The confirmation block to display

    Returns:
        Tuple of (approved, feedback_message)
    """
    print("\n" + "=" * 80)
    print("🛑 STREAM PAUSED - CONFIRMATION REQUIRED")
    print("=" * 80)

    metadata = block.metadata
    content = block.content

    # Display the confirmation prompt
    print(f"\n⚠️  {content.prompt}")
    print("\n" + "-" * 80)
    print(content.message)
    print("-" * 80)

    # Detect operation type from the message
    message_lower = content.message.lower()
    is_create = "create" in message_lower
    is_delete = "delete" in message_lower
    is_write = "write" in message_lower

    # Display options
    print("\nOptions:")
    print(f"  1. {metadata.confirm_label}")
    print(f"  2. {metadata.cancel_label}")
    print("  3. Approve with modifications")

    # Get user input
    while True:
        choice = input("\nYour choice (1-3): ").strip()

        if choice == "1":
            # Approved - generic feedback
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

        if choice == "2":
            # Rejected - generic feedback with suggestions
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

        if choice == "3":
            # Approved with modifications
            print("\nProvide your modifications/instructions:")
            modifications = input("> ").strip()

            feedback = f"""I approve this operation with the following modifications:

{modifications}

Please apply these changes and proceed with this operation.
After this operation is complete, please ask for confirmation for the next operation."""
            return True, feedback

        print("❌ Invalid choice. Please enter 1, 2, or 3.")


async def process_with_live_feedback(
    stream: PausableGeminiStream,
    processor: StreamBlockProcessor,
    initial_prompt: str,
    system_prompt: str,
) -> None:
    """Process the LLM stream with live feedback capability.

    This function orchestrates the main workflow:
    1. Starts processing the LLM stream
    2. Monitors for confirmation blocks
    3. Pauses the stream when confirmation is needed
    4. Collects user feedback
    5. Resumes the stream with feedback injected

    Args:
        stream: The pausable Gemini stream
        processor: StreamBlocks processor
        initial_prompt: Initial user prompt
        system_prompt: System instructions
    """
    extracted_blocks: list[ExtractedBlock[BaseMetadata, BaseContent]] = []
    confirmation_count = 0

    print("🚀 Starting live feedback example...")
    print("=" * 80)
    print(f"Task: {initial_prompt}")
    print("=" * 80)

    # Start processing the stream
    async for event in processor.process_stream(stream.stream(initial_prompt, system_prompt)):
        if event.type == EventType.RAW_TEXT:
            # Display raw text from LLM
            text = event.data.strip()
            if text:
                print(f"💬 {text}")

        elif event.type == EventType.BLOCK_EXTRACTED:
            block = event.block
            extracted_blocks.append(block)
            block_type = block.metadata.block_type

            print(f"\n✅ Block Extracted: {block.metadata.id} ({block_type})")

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

                    print(f"\n{icon} {metadata.title or 'Message'}")
                    print("-" * 60)
                    print(content.raw_content.strip())
                    print("-" * 60)

            elif block_type == "files_operations":
                if isinstance(block.metadata, FileOperationsMetadata) and isinstance(
                    block.content, FileOperationsContent
                ):
                    metadata = block.metadata
                    content = block.content

                    print(f"\n📁 File Operations: {metadata.id}")
                    if metadata.description:
                        print(f"   Description: {metadata.description}")

                    for op in content.operations:
                        icon = {"create": "✅", "edit": "📝", "delete": "❌"}.get(op.action, "❓")
                        print(f"   {icon} {op.action.upper()}: {op.path}")

            elif block_type == "file_content":
                if isinstance(block.metadata, FileContentMetadata) and isinstance(block.content, FileContentContent):
                    metadata = block.metadata
                    content = block.content

                    print(f"\n📄 File Content: {metadata.file}")
                    if metadata.description:
                        print(f"   Description: {metadata.description}")

                    lines = content.raw_content.strip().split("\n")
                    print(f"   Preview ({len(lines)} lines):")
                    for i, line in enumerate(lines[:5]):
                        print(f"     {i + 1}: {line}")
                    if len(lines) > 5:
                        print(f"     ... and {len(lines) - 5} more lines")

            elif block_type == "confirm":
                # CRITICAL: Confirmation block detected!
                if isinstance(block.metadata, ConfirmMetadata) and isinstance(block.content, ConfirmContent):
                    confirmation_count += 1

                    # Display confirmation and get user response
                    approved, feedback = display_confirmation(
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

        elif event.type == EventType.BLOCK_DELTA:
            # Show progress indicator
            print(".", end="", flush=True)

        elif event.type == EventType.BLOCK_REJECTED:
            print(f"\n⚠️  Block rejected: {event.reason}")

    # Summary
    print("\n\n" + "=" * 80)
    print("📊 EXECUTION SUMMARY")
    print("=" * 80)
    print(f"✅ Total blocks extracted: {len(extracted_blocks)}")
    print(f"🛑 Confirmations requested: {confirmation_count}")

    # Count by type
    block_counts: dict[str, int] = {}
    for block in extracted_blocks:
        bt = block.metadata.block_type
        block_counts[bt] = block_counts.get(bt, 0) + 1

    print("\nBlocks by type:")
    for bt, count in sorted(block_counts.items()):
        print(f"  - {bt}: {count}")

    print("\n✅ Example completed!")


async def main() -> None:
    """Run the live feedback example."""
    print("🎯 StreamBlocks Live Feedback Example - Per-Operation Confirmations")
    print("=" * 80)
    print("\nThis example demonstrates:")
    print("  • LLM stream processing for a realistic refactoring task")
    print("  • Real-time block extraction from the stream")
    print("  • MULTIPLE stream pauses - one for EACH file operation")
    print("  • User feedback insertion after each confirmation")
    print("  • Stream resume with updated context")
    print("  • Step-by-step interactive workflow")
    print("=" * 80)

    # Check for API key
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("\n❌ Error: Please set GOOGLE_API_KEY or GEMINI_API_KEY environment variable")
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
    registry.register("confirm", Confirm)
    registry.register("files_operations", FileOperations)
    registry.register("file_content", FileContent)
    registry.register("message", Message)

    # Create processor
    processor = StreamBlockProcessor(registry, lines_buffer=10)

    task = """I need to refactor our legacy authentication system to use OAuth2.

The current system has:
- Legacy password-based auth in src/legacy/auth.py
- Session management in src/legacy/session_manager.py
- User models in src/legacy/user_model.py

Please help me migrate to OAuth2 with JWT tokens.

IMPORTANT: This is a production system, so I need you to:
1. First, explain your migration approach
2. Ask for my confirmation BEFORE EACH file operation (creating, editing, deleting)
3. Process ONE file at a time - wait for my approval before proceeding to the next
4. Create the new OAuth2 implementation step-by-step
5. Provide tests for the new system

I want to review and approve EVERY operation individually before it's executed.
Safety is critical - no batch operations allowed."""

    # Process with live feedback
    await process_with_live_feedback(stream, processor, task, system_prompt)


if __name__ == "__main__":
    asyncio.run(main())
