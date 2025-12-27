#!/usr/bin/env python3
"""Example 13: Manual Chunk Processing.

This example shows how to process chunks manually using process_chunk()
instead of the automatic process_stream() method. This gives you fine-grained
control over when and how chunks are processed.

Use cases for manual chunk processing:
- Custom buffering strategies
- Processing chunks from multiple sources
- Integrating with existing async pipelines
- Batch processing with custom logic
- Selective processing based on chunk content

REQUIREMENTS:
- pip install streamblocks[gemini]
- Set GOOGLE_API_KEY or GEMINI_API_KEY environment variable
"""

import asyncio
import os
import sys
from collections.abc import AsyncIterator
from typing import Any

# Check for Gemini SDK
try:
    from google import genai
except ImportError:
    print("Error: google-genai package not installed.")
    print("Install it with: pip install streamblocks[gemini]")
    print("Or: pip install google-genai")
    sys.exit(1)

from hother.streamblocks import (
    BlockEndEvent,
    DelimiterPreambleSyntax,
    Registry,
    StreamBlockProcessor,
    TextDeltaEvent,
)
from hother.streamblocks_examples.blocks.agent.files import FileOperations


async def get_gemini_response(prompt: str | None = None) -> AsyncIterator[Any]:
    """Get Gemini API response stream."""
    # Get API key
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        msg = (
            "Please set GOOGLE_API_KEY or GEMINI_API_KEY environment variable.\n"
            "Get your key at: https://aistudio.google.com/apikey"
        )
        raise ValueError(msg)

    # Create client
    client = genai.Client(api_key=api_key)  # type: ignore[attr-defined]

    # Default prompt
    default_prompt = """Create a simple project structure with these files:
- src/main.py
- src/utils.py
- tests/test_main.py

Use this EXACT format (DO NOT use markdown code fences or any other formatting):

!!project:files_operations
src/main.py:C
src/utils.py:C
tests/test_main.py:C
!!end

IMPORTANT:
- Start your response directly with !! (no markdown, no code fences, no backticks)
- The first characters must be !!project:files_operations
- End with !!end on its own line

"""

    # Return the stream
    return await client.aio.models.generate_content_stream(  # type: ignore[attr-defined]
        model="gemini-2.5-flash",
        contents=prompt or default_prompt,
    )


async def example_basic_manual_processing() -> None:
    """Example 1: Basic manual chunk processing."""
    print("=" * 60)
    print("Example 1: Basic Manual Processing")
    print("=" * 60)
    print()

    # Setup processor
    syntax = DelimiterPreambleSyntax()
    registry = Registry(syntax=syntax)
    registry.register("files_operations", FileOperations)
    processor = StreamBlockProcessor(registry)

    print("Processing chunks manually...")
    print()

    # Get stream
    response = await get_gemini_response()

    # Process chunks manually
    chunk_count = 0
    event_count = 0

    async for chunk in response:  # type: ignore[var-annotated]
        chunk_count += 1

        # Process this chunk and get all events it produces
        events = processor.process_chunk(chunk)

        # Handle each event
        for event in events:
            event_count += 1

            # Original Gemini chunks
            if hasattr(event, "__module__") and "google.genai" in event.__module__:
                print(f"🔵 Chunk #{chunk_count}: Gemini event")

            # Text deltas
            elif isinstance(event, TextDeltaEvent):
                status = "inside block" if event.inside_block else "outside block"
                print(f"📝 Chunk #{chunk_count}: Text delta ({status})")

            # Extracted blocks
            elif isinstance(event, BlockEndEvent):
                block = event.get_block()
                if block is None:
                    continue
                print(f"\n✅ Chunk #{chunk_count}: Block extracted!")
                print(block.model_dump_json(indent=2))
                print()

    # Finalize to process remaining text and get any rejection events
    final_events = processor.finalize()
    for event in final_events:
        event_count += 1

        if isinstance(event, BlockEndEvent):
            block = event.get_block()
            if block is None:
                continue
            print("\n✅ Finalize: Block extracted!")
            print(block.model_dump_json(indent=2))
            print()
        elif isinstance(event, TextDeltaEvent):
            print("📝 Finalize: Text delta (processing remaining text)")
        else:
            print(f"⚠️  Finalize: {event.type}")

    print()
    print(f"Processed {chunk_count} chunks → {event_count} events")
    print()


async def example_selective_processing() -> None:
    """Example 2: Selective chunk processing with custom logic."""
    print("=" * 60)
    print("Example 2: Selective Processing")
    print("=" * 60)
    print()

    # Setup processor
    syntax = DelimiterPreambleSyntax()
    registry = Registry(syntax=syntax)
    registry.register("files_operations", FileOperations)
    processor = StreamBlockProcessor(registry)

    print("Only processing chunks with 'create' operations...")
    print()

    # Get stream
    response = await get_gemini_response()

    processed_chunks = 0
    skipped_chunks = 0

    async for chunk in response:  # type: ignore[var-annotated]
        # Get text from chunk (you could use adapter explicitly)
        text = getattr(chunk, "text", "")

        # Custom logic: only process chunks that might contain file operations
        if ":" in text and ("C" in text or "create" in text.lower()):
            events = processor.process_chunk(chunk)
            processed_chunks += 1

            for event in events:
                if isinstance(event, BlockEndEvent):
                    block = event.get_block()
                    if block is None:
                        continue
                    print("✅ Block Extracted:")
                    print(block.model_dump_json(indent=2))
                    print(f"   Found in chunk with text: {text[:50]}...")
        else:
            # Skip this chunk
            skipped_chunks += 1

    # Finalize to process remaining text and get any extracted blocks
    final_events = processor.finalize()
    for event in final_events:
        if isinstance(event, BlockEndEvent):
            block = event.get_block()
            if block is None:
                continue
            print("✅ Block from finalize:")
            print(block.model_dump_json(indent=2))

    print()
    print(f"Processed: {processed_chunks} chunks")
    print(f"Skipped: {skipped_chunks} chunks")
    print()


async def example_batch_processing() -> None:
    """Example 3: Batch processing with buffers."""
    print("=" * 60)
    print("Example 3: Batch Processing")
    print("=" * 60)
    print()

    # Setup processor
    syntax = DelimiterPreambleSyntax()
    registry = Registry(syntax=syntax)
    registry.register("files_operations", FileOperations)
    processor = StreamBlockProcessor(registry)

    print("Processing chunks in batches of 3...")
    print()

    # Get stream
    response = await get_gemini_response()

    chunk_buffer = []
    batch_size = 3
    batch_number = 0

    async for chunk in response:  # type: ignore[var-annotated]
        chunk_buffer.append(chunk)

        # Process when buffer is full
        if len(chunk_buffer) >= batch_size:
            batch_number += 1
            print(f"Processing batch #{batch_number} ({len(chunk_buffer)} chunks)...")

            for buffered_chunk in chunk_buffer:
                events = processor.process_chunk(buffered_chunk)

                for event in events:
                    if isinstance(event, BlockEndEvent):
                        block = event.get_block()
                        if block is None:
                            continue
                        print("  ✅ Block Extracted:")
                        print(block.model_dump_json(indent=2))

            chunk_buffer.clear()

    # Process remaining chunks
    if chunk_buffer:
        batch_number += 1
        print(f"Processing final batch #{batch_number} ({len(chunk_buffer)} chunks)...")

        for buffered_chunk in chunk_buffer:
            events = processor.process_chunk(buffered_chunk)

            for event in events:
                if isinstance(event, BlockEndEvent):
                    block = event.get_block()
                    if block is None:
                        continue
                    print("  ✅ Block Extracted:")
                    print(block.model_dump_json(indent=2))

    # Finalize to process remaining text and get any extracted blocks
    final_events = processor.finalize()
    for event in final_events:
        if isinstance(event, BlockEndEvent):
            block = event.get_block()
            if block is None:
                continue
            print("\n  ✅ Block from finalize:")
            print(block.model_dump_json(indent=2))

    print()
    print(f"Processed {batch_number} batches total")
    print()


async def main() -> None:
    """Run all examples."""
    print("🔧 StreamBlocks Manual Chunk Processing Examples")
    print()

    try:
        # Run all examples
        await example_basic_manual_processing()
        await example_selective_processing()
        await example_batch_processing()

        print("=" * 60)
        print("Summary")
        print("=" * 60)
        print()
        print("✅ Manual chunk processing with process_chunk()")
        print("✅ Custom processing logic and filtering")
        print("✅ Batch processing with buffers")
        print("✅ Finalization with finalize()")
        print()
        print("Key Benefits:")
        print("- Fine-grained control over processing")
        print("- Integration with existing pipelines")
        print("- Custom buffering and batching strategies")
        print("- Selective processing based on content")
        print()

    except ValueError as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
