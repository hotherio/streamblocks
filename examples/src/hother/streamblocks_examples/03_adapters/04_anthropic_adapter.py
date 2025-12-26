#!/usr/bin/env python3
"""Example 04: Anthropic Stream Adapter.

This example shows handling Anthropic's event-based streaming format.
Different event types (content_block_delta, message_stop, etc.) are preserved.

REQUIREMENTS:
- pip install streamblocks[anthropic]
- Set ANTHROPIC_API_KEY environment variable
"""

import asyncio
import os
import sys

# Check for Anthropic SDK
try:
    from anthropic import AsyncAnthropic
except ImportError:
    print("Error: anthropic package not installed.")
    print("Install it with: pip install streamblocks[anthropic]")
    print("Or: pip install anthropic")
    sys.exit(1)

from examples.blocks.agent.files import FileOperations
from hother.streamblocks import (
    AnthropicAdapter,
    BlockEndEvent,
    DelimiterPreambleSyntax,
    Registry,
    StreamBlockProcessor,
    TextDeltaEvent,
)


async def main() -> None:
    """Run the example."""
    print("=" * 60)
    print("Example 04: Anthropic Event Stream")
    print("=" * 60)
    print()

    # Get API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        msg = (
            "Please set ANTHROPIC_API_KEY environment variable.\n"
            "Get your key at: https://console.anthropic.com/settings/keys"
        )
        raise ValueError(msg)

    # Setup processor with explicit adapter
    syntax = DelimiterPreambleSyntax()
    registry = Registry(syntax=syntax)
    registry.register("files_operations", FileOperations)
    processor = StreamBlockProcessor(registry)
    adapter = AnthropicAdapter()

    # Create Anthropic client
    client = AsyncAnthropic(api_key=api_key)

    # Create prompt
    prompt = """Create a simple Python application with these files:
- app.py
- config.py

Use this EXACT format (DO NOT use markdown code fences):

!!files:files_operations
app.py:C
config.py:C
!!end

IMPORTANT:
- This block lists files to create (just the paths, no file content)
- Start your response directly with !! (no markdown, no code fences)
- Each line inside should be: filename:C (where C means Create)
- End with !!end on its own line
"""

    print("Connecting to Anthropic API...")
    print()

    try:
        # Get stream from Anthropic and pass directly to processor with explicit adapter
        async with client.messages.stream(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            async for event in processor.process_stream(stream, adapter=adapter):
                # Original Anthropic events - provider-agnostic detection
                if processor.is_native_event(event):
                    event_type = getattr(event, "type", None)
                    if event_type:
                        print(f"🟣 Anthropic Event: type={event_type}")
                        if event_type == "message_stop":
                            stop_reason = getattr(event, "stop_reason", None)
                            if stop_reason:
                                print(f"   🛑 Stop reason: {stop_reason}")

                # Text deltas
                elif isinstance(event, TextDeltaEvent):
                    print(f"📝 Delta: {repr(event.delta)[:40]}")

                # Blocks
                elif isinstance(event, BlockEndEvent):
                    block = event.get_block()
                    if block is None:
                        continue
                    print(f"\n✅ Block: {block.metadata.id}")
                    for op in block.content.operations:
                        print(f"   - {op.path}")
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
