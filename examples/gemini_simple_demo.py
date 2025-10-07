#!/usr/bin/env python3
"""
Simple Gemini Demo - Shows StreamBlocks working with Gemini API.

This simplified version uses a single syntax (delimiter with frontmatter) for all blocks.
"""

import asyncio
import os
import sys
from collections.abc import AsyncIterator
from typing import Literal

from google import genai
from pydantic import BaseModel, Field

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hother.streamblocks import (
    DelimiterFrontmatterSyntax,
    EventType,
    Registry,
    StreamBlockProcessor,
)
from hother.streamblocks.core.models import BaseContent, BlockDefinition


# Unified metadata model for all Gemini blocks
class GeminiBlockMetadata(BaseModel):
    """Metadata for Gemini AI blocks."""

    id: str
    block_type: Literal["file_operations", "file_content", "message"]
    description: str | None = None

    # File-specific fields (optional)
    file_path: str | None = None

    # Message-specific fields (optional)
    message_type: Literal["info", "warning", "error", "status"] | None = None


# Unified content model
class GeminiBlockContent(BaseContent):
    """Content for Gemini AI blocks."""

    @classmethod
    def parse(cls, raw_text: str) -> "GeminiBlockContent":
        """Parse content from raw text."""
        return cls(raw_content=raw_text.strip())


class GeminiBlock(BlockDefinition):
    """Unified block for all Gemini responses."""

    __metadata_class__ = GeminiBlockMetadata
    __content_class__ = GeminiBlockContent

    # From metadata:
    id: str
    block_type: Literal["file_operations", "file_content", "message"]
    description: str | None = None
    file_path: str | None = None
    message_type: Literal["info", "warning", "error", "status"] | None = None

    # From content:
    raw_content: str = ""


def create_simple_prompt() -> str:
    """Create a simple system prompt."""
    return """You are a helpful AI assistant. When responding, use this single block format for everything:

!!start
---
id: unique_id
block_type: file_operations | file_content | message
description: Brief description of what this block contains
file_path: path/to/file (only for file_content blocks)
message_type: info | warning | error | status (only for message blocks)
---
Content goes here
!!end

Examples:

1. For file operations:
!!start
---
id: create_files_01
block_type: file_operations
description: Creating initial project structure
---
src/main.py:C
src/utils.py:C
tests/test_main.py:C
README.md:C
!!end

2. For file content:
!!start
---
id: main_py_content
block_type: file_content
description: Main application entry point
file_path: src/main.py
---
def main():
    print("Hello, World!")

if __name__ == "__main__":
    main()
!!end

3. For messages/communication:
!!start
---
id: status_01
block_type: message
description: Explaining the approach
message_type: info
---
I'll create a simple Flask web application with proper structure and tests.
!!end

Always use this format for ALL content - whether it's file operations, code content, or communication."""


async def stream_from_gemini(prompt: str) -> AsyncIterator[str]:
    """Stream response from Gemini."""
    # Try GOOGLE_API_KEY first (official), then GEMINI_API_KEY
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        msg = "Please set GOOGLE_API_KEY or GEMINI_API_KEY environment variable"
        raise ValueError(msg)

    client = genai.Client(api_key=api_key)

    # Combine system prompt with user prompt
    system_prompt = create_simple_prompt()
    full_prompt = f"{system_prompt}\n\nUser: {prompt}"

    # Stream the response
    response = await client.aio.models.generate_content_stream(
        model="gemini-2.0-flash-exp",  # or "gemini-1.5-flash" for stable
        contents=full_prompt,
    )

    async for chunk in response:
        if chunk.text:
            yield chunk.text


async def main() -> None:
    """Run the simple Gemini demo."""
    print("🤖 StreamBlocks + Gemini Simple Demo")
    print("=" * 60)
    print("\nUsing unified delimiter + frontmatter syntax for all blocks")

    # Create a single syntax for all Gemini responses
    syntax = DelimiterFrontmatterSyntax(
        name="gemini_syntax",
        block_class=GeminiBlock,
        start_delimiter="!!start",
        end_delimiter="!!end",
    )

    # Create registry and processor
    registry = Registry(syntax)
    processor = StreamBlockProcessor(registry, lines_buffer=10)

    # Example prompts
    example_prompts = [
        "Create a Python hello world script with a README file",
        "Create a basic Flask web server with routes",
        "Write a function to calculate fibonacci numbers",
        "Create a simple calculator module with tests",
        "Explain how to use async/await in Python with examples",
    ]

    print("\nExample prompts:")
    for i, prompt in enumerate(example_prompts, 1):
        print(f"{i}. {prompt}")

    # Get user input
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg.isdigit() and 1 <= int(arg) <= len(example_prompts):
            user_prompt = example_prompts[int(arg) - 1]
        else:
            user_prompt = " ".join(sys.argv[1:])
    else:
        user_input = input("\nEnter your request (or 1-5 for examples, Enter for #1): ").strip()
        if user_input.isdigit() and 1 <= int(user_input) <= len(example_prompts):
            user_prompt = example_prompts[int(user_input) - 1]
        elif not user_input:
            user_prompt = example_prompts[0]
        else:
            user_prompt = user_input

    print(f"\n🚀 Processing: {user_prompt}")
    print("=" * 60)

    # Track extracted blocks
    extracted_blocks = []
    raw_text = []

    # Process the stream
    try:
        async for event in processor.process_stream(stream_from_gemini(user_prompt)):
            if event.type == EventType.BLOCK_EXTRACTED:
                block = event.metadata["extracted_block"]
                extracted_blocks.append(block)

                metadata: GeminiBlockMetadata = block.metadata
                content: GeminiBlockContent = block.content

                print(f"\n📦 Block: {metadata.id} ({metadata.block_type})")
                if metadata.description:
                    print(f"   Description: {metadata.description}")

                # Handle different block types
                if metadata.block_type == "file_operations":
                    # Parse file operations from content
                    lines = content.raw_content.strip().split("\n")
                    operations = {"create": [], "edit": [], "delete": []}

                    for line in lines:
                        if ":" in line:
                            path, op = line.rsplit(":", 1)
                            if op.upper() == "C":
                                operations["create"].append(path)
                            elif op.upper() == "E":
                                operations["edit"].append(path)
                            elif op.upper() == "D":
                                operations["delete"].append(path)

                    if operations["create"]:
                        print(f"   ✅ Create: {', '.join(operations['create'])}")
                    if operations["edit"]:
                        print(f"   ✏️  Edit: {', '.join(operations['edit'])}")
                    if operations["delete"]:
                        print(f"   ❌ Delete: {', '.join(operations['delete'])}")

                elif metadata.block_type == "file_content":
                    print(f"   📄 File: {metadata.file_path}")
                    # Show preview of content
                    lines = content.raw_content.split("\n")
                    preview_lines = 3
                    for i, line in enumerate(lines[:preview_lines]):
                        print(f"      {line}")
                    if len(lines) > preview_lines:
                        print(f"      ... ({len(lines) - preview_lines} more lines)")

                elif metadata.block_type == "message":
                    icons = {"info": "ℹ️ ", "warning": "⚠️ ", "error": "❌", "status": "📊"}
                    icon = icons.get(metadata.message_type, "💬")
                    print(f"   {icon} {metadata.message_type or 'message'}:")
                    # Show first few lines of message
                    lines = content.raw_content.split("\n")
                    for line in lines[:5]:
                        print(f"      {line}")
                    if len(lines) > 5:
                        print(f"      ... ({len(lines) - 5} more lines)")

            elif event.type == EventType.BLOCK_DELTA:
                # Show progress
                size = len(event.metadata.get("partial_block", {}).get("accumulated", ""))
                print(f"\r⏳ Processing block... {size} bytes", end="", flush=True)

            elif event.type == EventType.RAW_TEXT:
                # Collect any text outside blocks
                text = event.data.strip()
                if text:
                    raw_text.append(text)

            elif event.type == EventType.BLOCK_REJECTED:
                print(f"\n⚠️  Block rejected: {event.metadata['reason']}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()

    # Summary
    print(f"\n\n{'=' * 60}")
    print("SUMMARY:")
    print(f"  ✅ Extracted {len(extracted_blocks)} blocks")

    # Count block types
    block_types = {}
    for block in extracted_blocks:
        bt = block.metadata.block_type
        block_types[bt] = block_types.get(bt, 0) + 1

    for bt, count in sorted(block_types.items()):
        print(f"     - {bt}: {count}")

    if raw_text:
        print(f"\n  💬 Raw text lines: {len(raw_text)}")


if __name__ == "__main__":
    asyncio.run(main())
