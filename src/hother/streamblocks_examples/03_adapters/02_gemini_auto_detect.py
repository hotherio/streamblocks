#!/usr/bin/env python3
"""Example 02: Gemini Stream with Auto-Detection.

This example shows how StreamBlocks automatically detects
Gemini chunks and extracts text from them. No explicit
adapter configuration needed!

REQUIREMENTS:
- pip install streamblocks[gemini]
- Set GOOGLE_API_KEY or GEMINI_API_KEY environment variable
"""

import asyncio
import os
import sys

# Check for Gemini SDK
try:
    from google import genai
except ImportError:
    print("Error: google-genai package not installed.")
    print("Install it with: pip install streamblocks[gemini]")
    print("Or: pip install google-genai")
    sys.exit(1)

from hother.streamblocks import BlockEndEvent, Registry, StreamBlockProcessor, TextDeltaEvent
from hother.streamblocks_examples.blocks.agent.files import FileOperations


async def main() -> None:
    """Run the example."""
    print("=" * 60)
    print("Example 02: Gemini Auto-Detection")
    print("=" * 60)
    print()

    # Get API key
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        msg = (
            "Please set GOOGLE_API_KEY or GEMINI_API_KEY environment variable.\n"
            "Get your key at: https://aistudio.google.com/apikey"
        )
        raise ValueError(msg)

    # Setup processor
    registry = Registry()
    registry.register("files_operations", FileOperations)
    processor = StreamBlockProcessor(registry)

    # Create Gemini client
    client = genai.Client(api_key=api_key)  # type: ignore[attr-defined]

    # Create prompt
    prompt = """Create a simple project structure with these files:
- src/app.py
- README.md

Use this EXACT format (DO NOT use markdown code fences or any other formatting):

!!proj01:files_operations
src/app.py:C
README.md:C
!!end

IMPORTANT:
- Start your response directly with !! (no markdown, no code fences, no backticks)
- The first characters must be !!proj01:files_operations
- End with !!end on its own line
"""

    try:
        # Get stream from Gemini and pass directly to processor
        response = await client.aio.models.generate_content_stream(  # type: ignore[attr-defined]
            model="gemini-2.5-flash",
            contents=prompt,
        )

        async for event in processor.process_stream(response):
            # Original Gemini chunks (passed through)
            # Provider-agnostic detection using processor.is_native_event()
            if processor.is_native_event(event):
                text = getattr(event, "text", None)
                if text:
                    print(f"🔵 Gemini Chunk: text={repr(text)[:40]}")

                # Access Gemini-specific metadata
                usage = getattr(event, "usage_metadata", None)
                if usage:
                    total = getattr(usage, "total_token_count", None)
                    if total:
                        print(f"   📊 Total tokens: {total}")

            # Real-time text deltas
            elif isinstance(event, TextDeltaEvent):
                print(f"📝 Text Delta: {repr(event.delta)[:40]}", end="")
                if event.inside_block:
                    print(" (inside block)")
                else:
                    print()

            # Extracted blocks
            elif isinstance(event, BlockEndEvent):
                block = event.get_block()
                if block is None:
                    continue
                print("\n✅ Block Extracted:")
                print(block.model_dump_json(indent=2))
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
