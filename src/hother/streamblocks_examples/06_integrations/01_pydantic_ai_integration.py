#!/usr/bin/env python3
"""Example demonstrating PydanticAI integration with StreamBlocks.

This example shows how PydanticAI agents can transparently generate
StreamBlocks-compatible output that is extracted in real-time.
"""

import asyncio
import os
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING

from hother.streamblocks import DelimiterFrontmatterSyntax, Registry, StreamBlockProcessor
from hother.streamblocks.core.types import BlockEndEvent, TextContentEvent
from hother.streamblocks_examples.blocks.agent.files import FileContent, FileOperations

if TYPE_CHECKING:
    from hother.streamblocks.core.models import ExtractedBlock
    from hother.streamblocks.core.types import BaseContent, BaseMetadata

# Check if pydantic-ai is installed
try:
    from pydantic_ai import Agent
    from pydantic_ai.models.google import GoogleModel

    from hother.streamblocks.integrations.pydantic_ai import AgentStreamProcessor

    pydantic_ai_available = True
except ImportError:
    Agent = None
    GoogleModel = None
    AgentStreamProcessor = None
    pydantic_ai_available = False
    print("pydantic-ai is not installed. Install with: pip install pydantic-ai")


async def basic_example() -> None:
    """Basic example: Agent generates text with embedded blocks."""

    if not pydantic_ai_available or Agent is None or GoogleModel is None:
        print("⚠️  PydanticAI is not available")
        return

    # Create syntax for file operations
    file_ops_syntax = DelimiterFrontmatterSyntax(
        start_delimiter="!!start",
        end_delimiter="!!end",
    )

    # Create syntax for file content
    file_content_syntax = DelimiterFrontmatterSyntax(
        start_delimiter="!!start",
        end_delimiter="!!end",
    )

    # Create separate registries and register blocks
    file_ops_registry = Registry(syntax=file_ops_syntax)
    file_ops_registry.register("files_operations", FileOperations)

    file_content_registry = Registry(syntax=file_content_syntax)
    file_content_registry.register("file_content", FileContent)

    # Create a block-aware agent with custom system prompt
    system_prompt = """
You are a helpful assistant that creates structured content using blocks.

## Block Formats

### 1. File Operations Block
For listing files to create or delete:

!!start
---
id: files_001
block_type: files_operations
description: Creating project structure
---
src/main.py:C
src/utils.py:C
tests/test_main.py:C
README.md:C
!!end

Where: C=Create, D=Delete

### 2. File Content Block
For writing complete file contents:

!!start
---
id: file_001
block_type: file_content
file: src/config.py
description: Application configuration file
---
import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    app_name: str = "My Application"
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./app.db")

    class Config:
        env_file = ".env"

settings = Settings()
!!end

Mix explanatory text with structured blocks as appropriate.
"""

    prompt = """Create a Python project structure for a simple FastAPI web API.

Use blocks to:
1. First list all files to create using a files_operations block
2. Then provide the content for the main application file using a file_content block

Make sure to include proper project structure with an app module and a simple FastAPI application."""

    print("🤖 PydanticAI Agent with StreamBlocks Integration")
    print("=" * 60)
    print(f"Prompt: {prompt}")
    print("=" * 60)

    # Note: StreamBlocks design principle - one processor handles one syntax type
    # For multiple block types, we demonstrate processing the raw stream multiple times

    # Get the raw stream from a standard PydanticAI agent
    # agent = Agent(model="openai:gpt-4o", system_prompt=system_prompt)

    model = GoogleModel("gemini-2.5-flash")
    agent = Agent(model=model, system_prompt=system_prompt)

    print("\n[STREAMING] Receiving response from AI...")
    raw_text = ""
    async with agent.run_stream(prompt) as result:
        async for delta in result.stream_text(delta=True):
            raw_text += delta

    print("[COMPLETE] AI response received\n")

    # Collect all extracted blocks
    extracted_blocks: list[ExtractedBlock[BaseMetadata, BaseContent]] = []

    # Helper to create a stream from text
    async def text_stream():
        yield raw_text

    # Process stream for file operations blocks
    print("📂 Processing for file operations blocks...")
    file_ops_processor = StreamBlockProcessor(file_ops_registry)

    # Direct stream passing
    stream1 = text_stream()
    async for event in file_ops_processor.process_stream(stream1):
        if isinstance(event, BlockEndEvent):
            block = event.get_block()
            if block is None:
                continue
            # Only process blocks of the expected type
            if block.metadata.block_type == "files_operations":
                extracted_blocks.append(block)

                print("\n📦 EXTRACTED BLOCK:")
                print(block.model_dump_json(indent=2))

    # Process same stream for file content blocks
    print("\n📄 Processing for file content blocks...")
    file_content_processor = StreamBlockProcessor(file_content_registry)

    # Direct stream passing (create new stream instance)
    stream2 = text_stream()
    async for event in file_content_processor.process_stream(stream2):
        if isinstance(event, BlockEndEvent):
            block = event.get_block()
            if block is None:
                continue
            # Only process blocks of the expected type
            if block.metadata.block_type == "file_content":
                extracted_blocks.append(block)

                # Type narrowing for FileContentMetadata and FileContentContent
                from hother.streamblocks_examples.blocks.agent.files import FileContentContent, FileContentMetadata

                if not isinstance(block.metadata, FileContentMetadata):
                    continue
                if not isinstance(block.content, FileContentContent):
                    continue

                metadata = block.metadata
                content = block.content

                print(f"\n📄 EXTRACTED BLOCK: {metadata.id}")
                print(f"   Type: {metadata.block_type}")
                print(f"   File: {metadata.file}")
                if metadata.description:
                    print(f"   Description: {metadata.description}")
                lines = content.raw_content.strip().split("\n")
                print(f"   Content preview ({len(lines)} lines):")
                preview_lines = 5
                for i, line in enumerate(lines[:preview_lines]):
                    print(f"     {i + 1}: {line}")
                if len(lines) > preview_lines:
                    print(f"     ... and {len(lines) - preview_lines} more lines")

    # Summary
    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  - Extracted {len(extracted_blocks)} blocks total")

    file_ops_count = sum(1 for b in extracted_blocks if b.metadata.block_type == "files_operations")
    file_content_count = sum(1 for b in extracted_blocks if b.metadata.block_type == "file_content")

    print(f"  - {file_ops_count} file operations blocks")
    print(f"  - {file_content_count} file content blocks")


async def advanced_example_with_standard_agent() -> None:
    """Advanced example: Using standard PydanticAI agent with StreamBlocks processor."""

    if not pydantic_ai_available or Agent is None or GoogleModel is None or AgentStreamProcessor is None:
        print("⚠️  PydanticAI is not available")
        return

    # Create a standard PydanticAI agent
    model = GoogleModel("gemini-2.5-flash")
    agent = Agent(
        model,
        system_prompt="""
You are a helpful assistant that creates structured content.

When creating file operations, use this format:
!!start
---
id: <unique_id>
block_type: files_operations
description: <what these operations do>
---
path/to/file:C  (C=Create, D=Delete)
another/file:C
!!end

Mix explanatory text with structured blocks.
""",
    )

    # Create StreamBlocks components
    syntax = DelimiterFrontmatterSyntax(
        start_delimiter="!!start",
        end_delimiter="!!end",
    )
    registry = Registry(syntax=syntax)
    registry.register("files_operations", FileOperations)
    processor = AgentStreamProcessor(registry)

    prompt = "Create a README.md and setup.py for a Python package called 'example'."

    print("\n🔄 Standard PydanticAI Agent + StreamBlocks Processor")
    print("=" * 60)

    # Stream from agent
    async def get_agent_stream() -> AsyncIterator[str]:
        async with agent.run_stream(prompt) as result:
            async for text in result.stream_text():
                yield text

    # Process the stream through StreamBlocks - direct stream passing
    stream = get_agent_stream()
    async for event in processor.process_agent_stream(stream):
        if isinstance(event, TextContentEvent):
            if event.content.strip():
                print(f"[TEXT] {event.content.strip()}")

        elif isinstance(event, BlockEndEvent):
            block = event.get_block()
            if block is None:
                continue
            print("\n📦 BLOCK:")
            print(block.model_dump_json(indent=2))


async def main() -> None:
    """Run all examples."""

    if not pydantic_ai_available:
        print("\n⚠️  pydantic-ai is required for this example.")
        print("Install with: pip install pydantic-ai")
        return

    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("\n⚠️  Please set OPENAI_API_KEY environment variable")
        print("Or use a different model like 'anthropic:claude-3-5-sonnet-latest'")
        return

    print("StreamBlocks + PydanticAI Integration Examples")
    print("=" * 60)

    # Run examples
    await basic_example()
    print("\n" + "=" * 60)

    await advanced_example_with_standard_agent()

    print("\n✅ Examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
