"""Example demonstrating the minimal API with no custom models."""

import asyncio
from typing import AsyncIterator

from streamblocks import (
    Registry,
    DelimiterPreambleSyntax,
    EventType,
    StreamBlockProcessor,
)


async def example_stream() -> AsyncIterator[str]:
    """Example stream with simple blocks."""
    text = """
This is a document with some blocks using the minimal API.

!!note01:notes
This is a simple note block.
No custom models needed!
The library handles everything.
!!end

Some text between blocks.

!!todo01:tasks
- Buy groceries
- Call mom
- Finish the report
!!end

!!code01:snippets
def hello():
    print("Hello, world!")
!!end

That's all folks!
"""
    
    # Chunk-based streaming
    chunk_size = 50
    for i in range(0, len(text), chunk_size):
        chunk = text[i:i + chunk_size]
        yield chunk
        await asyncio.sleep(0.01)


async def main() -> None:
    """Main example function."""
    # Create syntax with NO custom models - uses BaseMetadata and BaseContent
    syntax = DelimiterPreambleSyntax(name="base_syntax")
    
    # Create type-specific registry
    registry = Registry(syntax)
    
    # Create processor with the registry
    processor = StreamBlockProcessor(registry, lines_buffer=5)
    
    # Process stream
    print("Processing with minimal API...")
    print("-" * 60)
    
    blocks_extracted = []
    
    async for event in processor.process_stream(example_stream()):
        if event.type == EventType.RAW_TEXT:
            # Raw text passed through
            if event.data.strip():
                print(f"[TEXT] {event.data.strip()}")
                
        elif event.type == EventType.BLOCK_EXTRACTED:
            # Complete block extracted
            block = event.metadata["extracted_block"]
            blocks_extracted.append(block)
            
            print(f"\n[BLOCK] Extracted!")
            print(f"  ID: {block.metadata.id}")
            print(f"  Type: {block.metadata.block_type}")
            print(f"  Raw content preview: {block.content.raw_content[:50]}...")
            
            # All blocks have raw_content automatically
            lines = block.content.raw_content.split("\n")
            print(f"  Content lines: {len(lines)}")
            
        elif event.type == EventType.BLOCK_REJECTED:
            # Block rejected
            print(f"\n[REJECT] {event.metadata['reason']}")
    
    print("\n" + "-" * 60)
    print(f"Total blocks extracted: {len(blocks_extracted)}")
    
    # Summary
    print("\nBlock summary:")
    for i, block in enumerate(blocks_extracted, 1):
        print(f"  {i}. {block.metadata.id} ({block.metadata.block_type})")
    
    print("\n✓ Simple single-syntax processing - no custom models needed!")


if __name__ == "__main__":
    asyncio.run(main())