#!/usr/bin/env python3
"""Example 03: OpenAI Stream with Explicit Adapter.

This example shows how to use an explicit adapter for OpenAI streams.
Also demonstrates accessing finish_reason from original chunks.

REQUIREMENTS:
- pip install streamblocks[openai]
- Set OPENAI_API_KEY environment variable
"""

import asyncio
import os
import sys

# Check for OpenAI SDK
try:
    from openai import AsyncOpenAI
except ImportError:
    print("Error: openai package not installed.")
    print("Install it with: pip install streamblocks[openai]")
    print("Or: pip install openai")
    sys.exit(1)

from hother.streamblocks import (
    BlockEndEvent,
    DelimiterPreambleSyntax,
    OpenAIAdapter,
    Registry,
    StreamBlockProcessor,
    TextDeltaEvent,
)
from hother.streamblocks_examples.blocks.agent.files import FileOperations


async def main() -> None:
    """Run the example."""
    print("=" * 60)
    print("Example 03: OpenAI with Explicit Adapter")
    print("=" * 60)
    print()

    # Get API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        msg = "Please set OPENAI_API_KEY environment variable.\nGet your key at: https://platform.openai.com/api-keys"
        raise ValueError(msg)

    # Setup processor with explicit adapter
    syntax = DelimiterPreambleSyntax()
    registry = Registry(syntax=syntax)
    registry.register("files_operations", FileOperations)
    processor = StreamBlockProcessor(registry)
    adapter = OpenAIAdapter()

    # Create OpenAI client
    client = AsyncOpenAI(api_key=api_key)

    # Create prompt
    prompt = """Create files for a simple app using this EXACT format (DO NOT use markdown code fences):

!!files01:files_operations
main.py:C
test.py:C
!!end

IMPORTANT:
- Start your response directly with !! (no markdown, no code fences)
- First characters must be !!files01:files_operations
- End with !!end on its own line
"""

    print("Connecting to OpenAI API...")
    print()

    try:
        # Get stream from OpenAI and pass directly to processor with explicit adapter
        stream = await client.chat.completions.create(
            model="gpt-5-nano-2025-08-07",
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )

        async for event in processor.process_stream(stream, adapter=adapter):
            # Original OpenAI chunks - provider-agnostic detection
            if processor.is_native_event(event):
                choices = getattr(event, "choices", [])
                if choices:
                    choice = choices[0]
                    delta = getattr(choice, "delta", None)
                    if delta:
                        content = getattr(delta, "content", None)
                        if content:
                            print(f"🟢 OpenAI Chunk: {repr(content)[:40]}")

                    # Check for stream completion
                    finish_reason = getattr(choice, "finish_reason", None)
                    if finish_reason:
                        print(f"🏁 Stream Complete: {finish_reason}")

            # Text deltas
            elif isinstance(event, TextDeltaEvent):
                print(f"📝 Delta: {repr(event.delta)[:40]}", flush=True)

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
