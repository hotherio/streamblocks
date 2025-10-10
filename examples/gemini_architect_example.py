#!/usr/bin/env python3
"""
AI Software Architect Example using Google Gemini

This example demonstrates using StreamBlocks with Gemini to handle
multiple block types for software architecture tasks:
- File operations for creating project structures
- Patches for code modifications
- Tool calls for analysis
- Memory blocks for context
- Visualization blocks for diagrams
"""

from __future__ import annotations

import asyncio
import os
import sys
import traceback
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
from hother.streamblocks.blocks.memory import Memory, MemoryContent, MemoryMetadata
from hother.streamblocks.blocks.message import Message, MessageContent, MessageMetadata
from hother.streamblocks.blocks.patch import Patch, PatchContent, PatchMetadata
from hother.streamblocks.blocks.toolcall import ToolCall, ToolCallContent, ToolCallMetadata
from hother.streamblocks.blocks.visualization import Visualization, VisualizationContent, VisualizationMetadata

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from hother.streamblocks.core.models import ExtractedBlock
    from hother.streamblocks.core.types import BaseContent, BaseMetadata


def create_system_prompt() -> str:
    """Create the system prompt for multiple block types."""
    return """
You are an AI Software Architect. Use structured blocks to solve software engineering tasks.
All blocks use !!start and !!end delimiters with YAML frontmatter between --- delimiters.

## 1. File Operations Block
For creating, editing, or deleting files (ONLY lists file paths and operations, NOT file content):

!!start
---
id: files_001
block_type: files_operations
description: Creating initial project structure
---
src/main.py:C
src/models/user.py:C
src/utils/helpers.py:C
tests/test_main.py:C
README.md:C
!!end

Where: C=Create, D=Delete

IMPORTANT: File operations blocks ONLY contain file paths and operation types (C/D).
They do NOT contain the actual file content. Use patch blocks or file_content to edit or write content.

## 2. Patch Block
For modifying existing files with diffs:

!!start
---
id: patch_001
block_type: patch
file: src/main.py
description: Add error handling to main function
---
@@ -10,3 +10,6 @@
 def main():
     result = process_data()
+    if not result:
+        print("Error: Processing failed")
+        return 1
     return 0
!!end

Note: The 'file' field is REQUIRED for patch blocks.

## 3. Tool Call Block
For executing analysis or utility tools:

!!start
---
id: tool_001
block_type: tool_call
tool_name: analyze_dependencies
description: Analyze project dependencies
---
directory: ./src
include_dev: true
output_format: json
!!end

Note: The 'tool_name' field is REQUIRED for tool_call blocks.

## 4. Memory Block
For storing/recalling context:

!!start
---
id: memory_001
block_type: memory
memory_type: store
key: project_config
namespace: current_project
---
framework: FastAPI
database: PostgreSQL
cache: Redis
!!end

Note: The 'memory_type' and 'key' fields are REQUIRED for memory blocks.

How to use: always add in memory important information, notably the current tasks and todo.

## 5. Visualization Block
For creating diagrams and charts:

!!start
---
id: viz_001
block_type: visualization
viz_type: diagram
title: System Architecture
format: markdown
---
nodes:
  - Frontend
  - API Gateway
  - Backend Services
  - Database
  - Cache
edges:
  - [Frontend, API Gateway]
  - [API Gateway, Backend Services]
  - [Backend Services, Database]
  - [Backend Services, Cache]
!!end

Note: The 'viz_type' and 'title' fields are REQUIRED for visualization blocks.

## 6. File Content Block
For writing complete file contents (creates or overwrites entire file):

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

Note: The 'file' field is REQUIRED for file_content blocks.

## 7. Message Block
For communicating information, status updates, or explanations to the user:

!!start
---
id: msg_001
block_type: message
message_type: info
title: Project Setup Complete
priority: normal
description: Summary of the setup process
---
I've successfully created the FastAPI application structure with user authentication.
The project includes JWT-based authentication, SQLAlchemy models, and all necessary endpoints.

Key features implemented:
- User registration with password hashing
- JWT token generation and validation
- Protected routes requiring authentication
- SQLite database with SQLAlchemy ORM
!!end

Note: The 'message_type' field is REQUIRED for message blocks.
Message types: info, warning, error, success, status, explanation

IMPORTANT:
- Always include 'id' and 'block_type' fields (both required)
- Each block type has specific required fields as shown above
- Use descriptive IDs and clear descriptions
- You can generate multiple blocks to solve complex tasks
- Use !!start and !!end delimiters for all blocks
- The YAML frontmatter must be between --- delimiters

REQUIRED FIELDS SUMMARY:
- ALL blocks: id, block_type
- files_operations: (no additional required fields)
- patch: file (the file path to patch)
- tool_call: tool_name
- memory: memory_type, key
- visualization: viz_type, title
- file_content: file (the file path to write)
- message: message_type (info/warning/error/success/status/explanation)


# General workflow:

1. Create a plan and store it in memory
2. Create or remove files
3. Write or edit the files

IMPORTANT: Communicate as much as possible with the user.

"""


def setup_processor() -> StreamBlockProcessor:
    """Set up a single processor with unified syntax."""
    syntax = DelimiterFrontmatterSyntax(
        start_delimiter="!!start",
        end_delimiter="!!end",
    )

    # Create registry and register all block types
    registry = Registry(syntax=syntax)
    registry.register("files_operations", FileOperations)
    registry.register("patch", Patch)
    registry.register("tool_call", ToolCall)
    registry.register("memory", Memory)
    registry.register("visualization", Visualization)
    registry.register("file_content", FileContent)
    registry.register("message", Message)

    return StreamBlockProcessor(registry, lines_buffer=5)


async def process_file_operations(block: ExtractedBlock[BaseMetadata, BaseContent]) -> None:
    """Process a file operations block."""
    # Type narrow with isinstance checks
    if not isinstance(block.metadata, FileOperationsMetadata):
        return
    if not isinstance(block.content, FileOperationsContent):
        return

    metadata = block.metadata
    content = block.content

    print(f"\n📁 File Operations: {metadata.id}")
    if metadata.description:
        print(f"📝 {metadata.description}")

    # Group operations by type
    ops_by_type: dict[str, list[str]] = {"create": [], "edit": [], "delete": []}
    for op in content.operations:
        ops_by_type[op.action].append(op.path)

    print(f"📊 Total operations: {len(content.operations)}")

    if ops_by_type["create"]:
        print(f"\n✅ CREATE ({len(ops_by_type['create'])} files):")
        for path in ops_by_type["create"][:5]:
            print(f"   + {path}")

    if ops_by_type["edit"]:
        print(f"\n✏️  EDIT ({len(ops_by_type['edit'])} files):")
        for path in ops_by_type["edit"][:5]:
            print(f"   ~ {path}")

    if ops_by_type["delete"]:
        print(f"\n❌ DELETE ({len(ops_by_type['delete'])} files):")
        for path in ops_by_type["delete"][:5]:
            print(f"   - {path}")


async def process_patch(block: ExtractedBlock[BaseMetadata, BaseContent]) -> None:
    """Process a patch block."""
    # Type narrow with isinstance checks
    if not isinstance(block.metadata, PatchMetadata):
        return
    if not isinstance(block.content, PatchContent):
        return

    metadata = block.metadata
    content = block.content

    print(f"\n🔧 Patch: {metadata.id}")
    print(f"📄 File: {metadata.file}")
    if metadata.description:
        print(f"📝 {metadata.description}")

    # Show preview of diff
    diff_lines = content.diff.split("\n")[:10]
    print("\nDiff preview:")
    for line in diff_lines:
        if line.startswith(("+", "-")):
            print(f"  {line}")
        else:
            print(f"  {line}")


async def process_tool_call(block: ExtractedBlock[BaseMetadata, BaseContent]) -> None:
    """Process a tool call block."""
    # Type narrow with isinstance checks
    if not isinstance(block.metadata, ToolCallMetadata):
        return
    if not isinstance(block.content, ToolCallContent):
        return

    metadata = block.metadata
    content = block.content

    print(f"\n🛠️  Tool Call: {metadata.id}")
    print(f"🔧 Tool: {metadata.tool_name}")
    if metadata.description:
        print(f"📝 {metadata.description}")

    print("📊 Parameters:")
    for key, value in content.parameters.items():
        print(f"   - {key}: {value}")


async def process_memory(block: ExtractedBlock[BaseMetadata, BaseContent]) -> None:
    """Process a memory block."""
    # Type narrow with isinstance checks
    if not isinstance(block.metadata, MemoryMetadata):
        return
    if not isinstance(block.content, MemoryContent):
        return

    metadata = block.metadata
    content = block.content

    print(f"\n🧠 Memory: {metadata.id}")
    print(f"🔑 Type: {metadata.memory_type}")
    print(f"📍 Key: {metadata.key}")
    print(f"📦 Namespace: {metadata.namespace}")

    if metadata.memory_type == "store":
        print(f"💾 Storing value: {content.value}")
    elif metadata.memory_type == "recall":
        print("📖 Recalling value")
    elif metadata.memory_type == "list":
        print("📋 Listing keys")


async def process_visualization(block: ExtractedBlock[BaseMetadata, BaseContent]) -> None:
    """Process a visualization block."""
    # Type narrow with isinstance checks
    if not isinstance(block.metadata, VisualizationMetadata):
        return
    if not isinstance(block.content, VisualizationContent):
        return

    metadata = block.metadata
    content = block.content

    print(f"\n📊 Visualization: {metadata.id}")
    print(f"📈 Type: {metadata.viz_type}")
    print(f"📝 Title: {metadata.title}")
    print(f"📄 Format: {metadata.format}")

    # Show data preview
    if metadata.viz_type == "diagram":
        nodes = content.data.get("nodes", [])
        edges = content.data.get("edges", [])
        print(f"\n🔵 Nodes: {', '.join(str(n) for n in nodes[:5])}")
        if len(nodes) > 5:
            print(f"   ... and {len(nodes) - 5} more")
        print(f"🔗 Edges: {len(edges)}")
    else:
        print(f"\n📊 Data keys: {list(content.data.keys())}")


async def process_file_content(block: ExtractedBlock[BaseMetadata, BaseContent]) -> None:
    """Process a file content block."""
    # Type narrow with isinstance checks
    if not isinstance(block.metadata, FileContentMetadata):
        return
    if not isinstance(block.content, FileContentContent):
        return

    metadata = block.metadata
    content = block.content

    print(f"\n📄 File Content: {metadata.id}")
    print(f"📁 File: {metadata.file}")
    if metadata.description:
        print(f"📝 {metadata.description}")

    # Show content preview
    lines = content.raw_content.strip().split("\n")
    print(f"\n📊 Content preview ({len(lines)} lines):")
    for i, line in enumerate(lines[:10]):
        print(f"   {i + 1}: {line}")
    if len(lines) > 10:
        print(f"   ... and {len(lines) - 10} more lines")


async def process_message(block: ExtractedBlock[BaseMetadata, BaseContent]) -> None:
    """Process a message block."""
    # Type narrow with isinstance checks
    if not isinstance(block.metadata, MessageMetadata):
        return
    if not isinstance(block.content, MessageContent):
        return

    metadata = block.metadata
    content = block.content

    # Choose emoji based on message type
    emoji_map = {"info": "ℹ️", "warning": "⚠️", "error": "❌", "success": "✅", "status": "📊", "explanation": "💡"}
    emoji = emoji_map.get(metadata.message_type, "💬")

    print(f"\n{emoji} Message: {metadata.id}")
    if metadata.title:
        print(f"📝 {metadata.title}")
    print(f"🔖 Type: {metadata.message_type} | Priority: {metadata.priority}")

    # Display the message content
    print("\n" + "-" * 60)
    print(content.raw_content.strip())
    print("-" * 60)


async def stream_from_gemini(prompt: str) -> AsyncIterator[str]:
    """Stream response from Gemini."""
    # Try GOOGLE_API_KEY first (official), then GEMINI_API_KEY
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        msg = "Please set GOOGLE_API_KEY or GEMINI_API_KEY environment variable"
        raise ValueError(msg)

    client = genai.Client(api_key=api_key)  # type: ignore[attr-defined]
    model_id = "gemini-2.5-flash"

    # Get system prompt
    system_prompt = create_system_prompt()
    full_prompt = f"{system_prompt}\n\nUser request: {prompt}"

    # Stream the response
    response = await client.aio.models.generate_content_stream(model=model_id, contents=full_prompt)  # type: ignore[attr-defined]
    async for chunk in response:  # type: ignore[var-annotated]
        if chunk.text:  # type: ignore[attr-defined]
            yield chunk.text  # type: ignore[attr-defined]


async def main() -> None:
    """Run the architect example."""
    print("🏗️  Gemini AI Architect - Multi-Block Demo")
    print("=" * 60)

    # Setup single unified processor
    processor = setup_processor()

    # Example prompts
    example_prompts = [
        "Create a FastAPI web application with user authentication",
        "Design a microservices architecture for an e-commerce platform",
        "Add error handling and logging to an existing Python application",
        "Create a data pipeline with PostgreSQL and Redis",
        "Build a REST API with database models and tests",
    ]

    print("\nExample prompts:")
    for i, prompt in enumerate(example_prompts, 1):
        print(f"{i}. {prompt}")

    # Get user input
    user_prompt = input("\nEnter your request (or 1-5 for examples): ").strip()

    # Handle example selection
    if user_prompt.isdigit():
        example_num = int(user_prompt)
        if 1 <= example_num <= len(example_prompts):
            user_prompt = example_prompts[example_num - 1]
        else:
            user_prompt = example_prompts[0]
    elif not user_prompt:
        user_prompt = example_prompts[0]

    print(f"\n🚀 Processing: {user_prompt}")
    print("=" * 60)

    # Track blocks by type
    blocks_by_type = {
        "files_operations": 0,
        "patch": 0,
        "tool_call": 0,
        "memory": 0,
        "visualization": 0,
        "file_content": 0,
        "message": 0,
    }

    try:
        # Process the Gemini stream
        gemini_stream = stream_from_gemini(user_prompt)

        async for event in processor.process_stream(gemini_stream):
            if event.type == EventType.BLOCK_EXTRACTED:
                block = event.block
                block_type = block.metadata.block_type
                blocks_by_type[block_type] += 1

                print(f"\n{'=' * 60}")
                print(f"📦 Block extracted: {block_type}")
                print(f"{'=' * 60}")

                # Process based on type
                if block_type == "files_operations":
                    await process_file_operations(block)
                elif block_type == "patch":
                    await process_patch(block)
                elif block_type == "tool_call":
                    await process_tool_call(block)
                elif block_type == "memory":
                    await process_memory(block)
                elif block_type == "visualization":
                    await process_visualization(block)
                elif block_type == "file_content":
                    await process_file_content(block)
                elif block_type == "message":
                    await process_message(block)

            elif event.type == EventType.RAW_TEXT:
                text = event.data.strip()
                if text:
                    print(f"\n💬 {text}")

            elif event.type == EventType.BLOCK_REJECTED:
                reason = event.reason
                print(f"\n⚠️  Block rejected: {reason}")
                # Show the raw data that was rejected
                preview = event.data[:200] if len(event.data) > 200 else event.data
                print(f"   Raw data preview: {preview!r}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        traceback.print_exc()

    # Summary
    print(f"\n\n{'=' * 60}")
    print("📊 SUMMARY")
    print(f"{'=' * 60}")
    total_blocks = sum(blocks_by_type.values())
    print(f"✅ Total blocks extracted: {total_blocks}")
    print("\nBreakdown by type:")
    for block_type, count in blocks_by_type.items():
        if count > 0:
            print(f"  - {block_type}: {count}")


if __name__ == "__main__":
    asyncio.run(main())
