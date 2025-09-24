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
from collections.abc import AsyncIterator
from typing import Any

from google import genai

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from streamblocks import (
    DelimiterFrontmatterSyntax,
    EventType,
    Registry,
    StreamBlockProcessor,
)
from streamblocks.content import (
    FileContentContent,
    FileContentMetadata,
    FileOperationsContent,
    FileOperationsMetadata,
    MemoryContent,
    MemoryMetadata,
    MessageContent,
    MessageMetadata,
    PatchContent,
    PatchMetadata,
    ToolCallContent,
    ToolCallMetadata,
    VisualizationContent,
    VisualizationMetadata,
)
from streamblocks.core.models import BaseContent, BaseMetadata, BlockCandidate
from streamblocks.core.types import ParseResult


class UnifiedMetadata(BaseMetadata):
    """Unified metadata that can represent any block type."""

    # Common fields
    description: str | None = None

    # FileOperations fields
    type: str | None = None  # Alias for compatibility

    # Patch fields
    file: str | None = None

    # ToolCall fields
    tool_name: str | None = None

    # Memory fields
    memory_type: str | None = None
    key: str | None = None
    namespace: str = "default"
    ttl_seconds: int | None = None

    # Visualization fields
    viz_type: str | None = None
    title: str | None = None
    format: str = "markdown"
    width: int | None = None
    height: int | None = None

    # Message fields
    message_type: str | None = None
    priority: str = "normal"


class UnifiedContent(BaseContent):
    """Unified content that routes to appropriate content class."""

    @classmethod
    def parse(cls, raw_text: str) -> Any:
        """This should not be called directly."""
        # Return a placeholder - actual parsing happens in the syntax
        return cls(raw_content=raw_text)


class UnifiedSyntax(DelimiterFrontmatterSyntax):
    """Syntax that dynamically routes to appropriate metadata/content classes."""

    def __init__(self, name: str = "unified_syntax"):
        # Initialize with unified classes
        super().__init__(
            name=name,
            metadata_class=UnifiedMetadata,
            content_class=UnifiedContent,
            start_delimiter="!!start",
            end_delimiter="!!end"
        )

    def parse_block(self, candidate: BlockCandidate) -> ParseResult[Any, Any]:
        """Parse block and route to appropriate classes based on block_type."""
        # First, parse to get the block_type
        result = super().parse_block(candidate)
        if not result.success:
            return result

        # Get the block_type from metadata
        unified_metadata = result.metadata
        block_type = unified_metadata.block_type

        # Route to appropriate classes based on block_type
        try:
            content_text = "\n".join(candidate.content_lines)

            metadata_dict = unified_metadata.model_dump()

            if block_type == "files_operations":
                metadata_dict["type"] = "files_operations"  # Required by FileOperationsMetadata
                metadata = FileOperationsMetadata(**metadata_dict)
                # Extract only the file operation lines (before any --- separator)
                content_lines = content_text.strip().split('\n')
                file_ops_lines = []
                for line in content_lines:
                    if line.strip() == '---':
                        break  # Stop at separator
                    if line.strip() and ':' in line:
                        file_ops_lines.append(line)
                clean_content = '\n'.join(file_ops_lines)
                content = FileOperationsContent.parse(clean_content)
            elif block_type == "patch":
                metadata_dict["type"] = "patch"  # Required by PatchMetadata
                metadata = PatchMetadata(**metadata_dict)
                content = PatchContent.parse(content_text)
            elif block_type == "tool_call":
                metadata = ToolCallMetadata(**unified_metadata.model_dump())
                content = ToolCallContent.parse(content_text)
            elif block_type == "memory":
                metadata = MemoryMetadata(**unified_metadata.model_dump())
                content = MemoryContent.parse(content_text)
            elif block_type == "visualization":
                metadata = VisualizationMetadata(**unified_metadata.model_dump())
                content = VisualizationContent.parse(content_text)
            elif block_type == "file_content":
                metadata = FileContentMetadata(**unified_metadata.model_dump())
                content = FileContentContent.parse(content_text)
            elif block_type == "message":
                metadata = MessageMetadata(**unified_metadata.model_dump())
                content = MessageContent.parse(content_text)
            else:
                return ParseResult(success=False, error=f"Unknown block_type: {block_type}")

            return ParseResult(success=True, metadata=metadata, content=content)
        except Exception as e:
            # Provide more detailed error information
            error_msg = f"Failed to parse {block_type} block: {str(e)}"
            if hasattr(e, '__class__'):
                error_msg = f"{e.__class__.__name__}: {str(e)}"
            return ParseResult(success=False, error=error_msg)


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
    syntax = UnifiedSyntax()
    registry = Registry(syntax)
    return StreamBlockProcessor(registry, lines_buffer=5)


async def process_file_operations(block):
    """Process a file operations block."""
    metadata: FileOperationsMetadata = block.metadata
    content: FileOperationsContent = block.content

    print(f"\n📁 File Operations: {metadata.id}")
    if metadata.description:
        print(f"📝 {metadata.description}")

    # Group operations by type
    ops_by_type = {"create": [], "edit": [], "delete": []}
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


async def process_patch(block):
    """Process a patch block."""
    metadata: PatchMetadata = block.metadata
    content: PatchContent = block.content

    print(f"\n🔧 Patch: {metadata.id}")
    print(f"📄 File: {metadata.file}")
    if metadata.description:
        print(f"📝 {metadata.description}")

    # Show preview of diff
    diff_lines = content.diff.split("\n")[:10]
    print("\nDiff preview:")
    for line in diff_lines:
        if line.startswith("+") or line.startswith("-"):
            print(f"  {line}")
        else:
            print(f"  {line}")


async def process_tool_call(block):
    """Process a tool call block."""
    metadata: ToolCallMetadata = block.metadata
    content: ToolCallContent = block.content

    print(f"\n🛠️  Tool Call: {metadata.id}")
    print(f"🔧 Tool: {metadata.tool_name}")
    if metadata.description:
        print(f"📝 {metadata.description}")

    print("📊 Parameters:")
    for key, value in content.parameters.items():
        print(f"   - {key}: {value}")


async def process_memory(block):
    """Process a memory block."""
    metadata: MemoryMetadata = block.metadata
    content: MemoryContent = block.content

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


async def process_visualization(block):
    """Process a visualization block."""
    metadata: VisualizationMetadata = block.metadata
    content: VisualizationContent = block.content

    print(f"\n📊 Visualization: {metadata.id}")
    print(f"📈 Type: {metadata.viz_type}")
    print(f"📝 Title: {metadata.title}")
    print(f"📄 Format: {metadata.format}")

    # Show data preview
    if metadata.viz_type == "diagram":
        nodes = content.data.get("nodes", [])
        edges = content.data.get("edges", [])
        print(f"\n🔵 Nodes: {', '.join(nodes[:5])}")
        if len(nodes) > 5:
            print(f"   ... and {len(nodes) - 5} more")
        print(f"🔗 Edges: {len(edges)}")
    else:
        print(f"\n📊 Data keys: {list(content.data.keys())}")


async def process_file_content(block):
    """Process a file content block."""
    metadata: FileContentMetadata = block.metadata
    content: FileContentContent = block.content

    print(f"\n📄 File Content: {metadata.id}")
    print(f"📁 File: {metadata.file}")
    if metadata.description:
        print(f"📝 {metadata.description}")

    # Show content preview
    lines = content.raw_content.strip().split('\n')
    print(f"\n📊 Content preview ({len(lines)} lines):")
    for i, line in enumerate(lines[:10]):
        print(f"   {i+1}: {line}")
    if len(lines) > 10:
        print(f"   ... and {len(lines) - 10} more lines")


async def process_message(block):
    """Process a message block."""
    metadata: MessageMetadata = block.metadata
    content: MessageContent = block.content

    # Choose emoji based on message type
    emoji_map = {
        "info": "ℹ️",
        "warning": "⚠️",
        "error": "❌",
        "success": "✅",
        "status": "📊",
        "explanation": "💡"
    }
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
        raise ValueError("Please set GOOGLE_API_KEY or GEMINI_API_KEY environment variable")

    client = genai.Client(api_key=api_key)
    model_id = "gemini-2.5-flash"

    # Get system prompt
    system_prompt = create_system_prompt()
    full_prompt = f"{system_prompt}\n\nUser request: {prompt}"

    # Stream the response
    response = await client.aio.models.generate_content_stream(model=model_id, contents=full_prompt)
    async for chunk in response:
        if chunk.text:
            yield chunk.text


async def main():
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
                block = event.metadata["extracted_block"]
                block_type = block.metadata.block_type
                blocks_by_type[block_type] += 1

                print(f"\n{'='*60}")
                print(f"📦 Block extracted: {block_type}")
                print(f"{'='*60}")

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
                reason = event.metadata.get('reason', 'Unknown')
                print(f"\n⚠️  Block rejected: {reason}")
                # Show more details about the rejection
                if 'raw_text' in event.metadata:
                    preview = event.metadata['raw_text'][:200]
                    print(f"   Preview: {preview}...")
                else:
                    # Show the raw data that was rejected
                    preview = event.data[:200] if len(event.data) > 200 else event.data
                    print(f"   Raw data preview: {repr(preview)}")

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
