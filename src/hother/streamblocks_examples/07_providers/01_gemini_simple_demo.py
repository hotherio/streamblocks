#!/usr/bin/env python3
"""
Simple Gemini Demo - Shows StreamBlocks working with Gemini API.

This simplified version uses a single syntax (delimiter with frontmatter) for all blocks.

REQUIREMENTS:
- pip install streamblocks[gemini]
- Set GOOGLE_API_KEY or GEMINI_API_KEY environment variable
"""

import asyncio
import os
import sys
from collections.abc import AsyncIterator
from textwrap import dedent
from typing import TYPE_CHECKING, Any

# Check for Gemini SDK
try:
    from google import genai  # type: ignore[import-not-found]
except ImportError:
    print("Error: google-genai package not installed.")
    print("Install it with: pip install streamblocks[gemini]")
    print("Or: pip install google-genai")
    sys.exit(1)

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hother.streamblocks import (
    BlockContentDeltaEvent,
    BlockEndEvent,
    BlockErrorEvent,
    BlockHeaderDeltaEvent,
    BlockMetadataDeltaEvent,
    DelimiterFrontmatterSyntax,
    Registry,
    StreamBlockProcessor,
    TextContentEvent,
)
from hother.streamblocks_examples.blocks.agent.files import (
    FileContent,
    FileContentContent,
    FileContentMetadata,
    FileOperations,
    FileOperationsContent,
    FileOperationsMetadata,
)
from hother.streamblocks_examples.blocks.agent.message import Message, MessageContent, MessageMetadata

if TYPE_CHECKING:
    from hother.streamblocks.core.models import ExtractedBlock
    from hother.streamblocks.core.types import BaseContent, BaseMetadata


def create_simple_prompt() -> str:
    """Create a simple system prompt."""
    return dedent("""
        You are a helpful AI assistant. When responding, use this single block format for everything:

        !!start
        ---
        id: unique_id
        block_type: files_operations | file_content | message
        ---
        Content goes here
        !!end

        Examples:

        1. For file operations (use block_type: files_operations):
        !!start
        ---
        id: create_files_01
        block_type: files_operations
        description: Creating initial project structure
        ---
        src/main.py:C
        src/utils.py:C
        tests/test_main.py:C
        README.md:C
        !!end

        Note: C=create, E=edit, D=delete

        2. For file content (use block_type: file_content, MUST include 'file' field):
        !!start
        ---
        id: main_py_content
        block_type: file_content
        file: src/main.py
        description: Main application entry point
        ---
        def main():
            print("Hello, World!")

        if __name__ == "__main__":
            main()
        !!end

        3. For messages/communication (use block_type: message, MUST include 'message_type'):
        !!start
        ---
        id: status_01
        block_type: message
        message_type: info
        title: Explaining the approach
        ---
        I'll create a simple Flask web application with proper structure and tests.
        !!end

        Note: message_type can be: info, warning, error, success, status, explanation

        Always use this format for ALL content - whether it's file operations, code content, or communication.
    """).strip()


async def get_gemini_response(prompt: str) -> AsyncIterator[Any]:
    """Get Gemini API response stream.

    Note: Returns the stream directly - no need for wrapper function!
    The StreamBlockProcessor will auto-detect Gemini chunks and use
    GeminiAdapter to extract text while preserving original chunks.
    """
    # Try GOOGLE_API_KEY first (official), then GEMINI_API_KEY
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        msg = "Please set GOOGLE_API_KEY or GEMINI_API_KEY environment variable"
        raise ValueError(msg)

    client = genai.Client(api_key=api_key)  # type: ignore[attr-defined]

    # Combine system prompt with user prompt
    system_prompt = create_simple_prompt()
    full_prompt = f"{system_prompt}\n\nUser: {prompt}"

    # Return the stream directly - no need to yield!
    return await client.aio.models.generate_content_stream(  # type: ignore[attr-defined]
        model="gemini-2.5-flash",
        contents=full_prompt,
    )


async def main() -> None:
    """Run the simple Gemini demo."""
    print("StreamBlocks + Gemini Simple Demo")
    print("=" * 60)
    print("\nUsing unified delimiter + frontmatter syntax for all blocks")

    # Create a single syntax for all Gemini responses
    syntax = DelimiterFrontmatterSyntax(
        start_delimiter="!!start",
        end_delimiter="!!end",
    )

    # Create registry and register all block types using default blocks
    registry = Registry(syntax=syntax)
    registry.register("files_operations", FileOperations)
    registry.register("file_content", FileContent)
    registry.register("message", Message)

    from hother.streamblocks.core.processor import ProcessorConfig

    config = ProcessorConfig(lines_buffer=10)
    processor = StreamBlockProcessor(registry, config=config)

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

    # Detect non-interactive mode
    is_non_interactive = (
        not sys.stdin.isatty()  # No TTY (piped/redirected)
        or os.getenv("CI")  # CI environment
        or os.getenv("NON_INTERACTIVE")  # Explicit flag
    )

    # Get user input
    if len(sys.argv) > 1:
        # Command-line argument provided
        arg = sys.argv[1]
        if arg.isdigit() and 1 <= int(arg) <= len(example_prompts):
            user_prompt = example_prompts[int(arg) - 1]
        else:
            user_prompt = " ".join(sys.argv[1:])
        print(f"\nUsing prompt from command line: {user_prompt}")
    elif is_non_interactive:
        # Non-interactive mode: use first example
        user_prompt = example_prompts[0]
        print("\nNon-interactive mode: using default prompt")
    else:
        # Interactive mode: ask user
        user_input = input("\nEnter your request (or 1-5 for examples, Enter for #1): ").strip()
        if user_input.isdigit() and 1 <= int(user_input) <= len(example_prompts):
            user_prompt = example_prompts[int(user_input) - 1]
        elif not user_input:
            user_prompt = example_prompts[0]
        else:
            user_prompt = user_input

    print(f"\nProcessing: {user_prompt}")
    print("=" * 60)

    # Track extracted blocks
    extracted_blocks: list[ExtractedBlock[BaseMetadata, BaseContent]] = []
    raw_text: list[str] = []

    # Process the stream
    try:
        # Get response and pass directly to processor
        response = await get_gemini_response(user_prompt)
        async for event in processor.process_stream(response):
            # Skip native Gemini events (we only care about StreamBlocks events)
            if processor.is_native_event(event):
                continue

            if isinstance(event, BlockEndEvent):
                block = event.get_block()
                if block is None:
                    continue
                extracted_blocks.append(block)

                # Handle different block types with proper type narrowing
                if block.metadata.block_type in ("files_operations", "file_content", "message"):
                    print(f"\nBlock extracted: {block.metadata.id}")
                    print(block.model_dump_json(indent=2))

            elif isinstance(event, (BlockHeaderDeltaEvent, BlockMetadataDeltaEvent, BlockContentDeltaEvent)):
                # Show progress
                print("\r Processing block...", end="", flush=True)

            elif isinstance(event, TextContentEvent):
                # Collect any text outside blocks
                text = event.content.strip()
                if text:
                    raw_text.append(text)

            elif isinstance(event, BlockErrorEvent):
                print(f"\nBlock rejected: {event.reason}")

    except Exception as e:
        print(f"\nError: {e}")
        import traceback

        traceback.print_exc()

    # Summary
    print(f"\n\n{'=' * 60}")
    print("SUMMARY:")
    print(f"  Extracted {len(extracted_blocks)} blocks")

    # Count block types
    block_types: dict[str, int] = {}
    for block in extracted_blocks:
        bt = block.metadata.block_type
        block_types[bt] = block_types.get(bt, 0) + 1

    for bt, count in sorted(block_types.items()):
        print(f"     - {bt}: {count}")

    if raw_text:
        print(f"\n  Raw text lines: {len(raw_text)}")


if __name__ == "__main__":
    asyncio.run(main())
