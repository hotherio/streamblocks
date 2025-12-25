"""Example demonstrating MarkdownFrontmatterSyntax with YAML frontmatter."""

import asyncio
from collections.abc import AsyncIterator
from textwrap import dedent
from typing import TYPE_CHECKING

from hother.streamblocks import MarkdownFrontmatterSyntax, Registry, StreamBlockProcessor
from hother.streamblocks.blocks.patch import Patch
from hother.streamblocks.core.types import (
    BlockContentDeltaEvent,
    BlockEndEvent,
    BlockErrorEvent,
    BlockHeaderDeltaEvent,
    BlockMetadataDeltaEvent,
    TextContentEvent,
)

if TYPE_CHECKING:
    from hother.streamblocks.core.models import ExtractedBlock
    from hother.streamblocks.core.types import BaseContent, BaseMetadata


async def example_stream() -> AsyncIterator[str]:
    """Example stream with markdown frontmatter blocks."""
    text = dedent("""
        Here's a document with some patches using markdown-style blocks with YAML frontmatter.

        ```patch
        ---
        id: security-fix
        block_type: patch
        file: auth.py
        start_line: 45
        ---
         def authenticate(user, password):
        -    if password == "admin": # pragma: allowlist secret
        +    if check_password_hash(user.password_hash, password):
                 return True
             return False
        ```

        Now let's add another patch for the config file:

        ```patch
        ---
        id: config-update
        block_type: patch
        file: config.yaml
        start_line: 10
        ---
         database:
           host: localhost
        -  port: 3306
        +  port: 5432
        -  driver: mysql
        +  driver: postgresql
        ```

        And here's a final patch with more metadata:

        ```patch
        ---
        id: feature-add
        block_type: patch
        file: features.py
        start_line: 100
        author: dev-team
        priority: high
        ---
        +def new_feature():
        +    \"\"\"Implement awesome new feature.\"\"\"
        +    return \"awesome\"
        +
         class ExistingClass:
             pass
        ```

        That's all for the patches!
    """)

    # Chunk-based streaming (simulating real network transfer)
    chunk_size = 80  # Larger chunks for markdown blocks
    for i in range(0, len(text), chunk_size):
        chunk = text[i : i + chunk_size]
        yield chunk
        await asyncio.sleep(0.01)


async def main() -> None:
    """Main example function."""
    # Create markdown frontmatter syntax for patch blocks
    # Note: In the new API, each Registry holds exactly one syntax.
    # To handle multiple info strings (patch/yaml/diff), you would need separate processors
    # or a custom syntax that handles multiple patterns internally.
    syntax = MarkdownFrontmatterSyntax(
        fence="```",
        info_string="patch",  # Will match ```patch blocks
    )

    # Create type-specific registry and register block
    registry = Registry(syntax=syntax)
    registry.register("patch", Patch)

    # Create processor with config
    from hother.streamblocks.core.processor import ProcessorConfig

    config = ProcessorConfig(lines_buffer=10)
    processor = StreamBlockProcessor(registry, config=config)

    # Process stream
    print("Processing markdown frontmatter blocks...")
    print("-" * 70)

    blocks_extracted: list[ExtractedBlock[BaseMetadata, BaseContent]] = []
    current_partial = None

    async for event in processor.process_stream(example_stream()):
        if isinstance(event, TextContentEvent):
            # Raw text passed through
            if event.content.strip():
                print(f"[TEXT] {event.content.strip()}")

        elif isinstance(event, (BlockHeaderDeltaEvent, BlockMetadataDeltaEvent, BlockContentDeltaEvent)):
            # Track partial block updates
            syntax = event.syntax
            section = event.type.value.replace("BLOCK_", "").replace("_DELTA", "").lower()
            if current_partial != syntax:
                print(f"\n[DELTA] Started {syntax} block (section: {section})")
                current_partial = syntax

        elif isinstance(event, BlockEndEvent):
            # Complete block extracted
            block = event.get_block()
            if block is None:
                continue
            blocks_extracted.append(block)
            current_partial = None

            # Type narrowing for patch blocks
            from hother.streamblocks.blocks.patch import PatchContent, PatchMetadata

            if not isinstance(block.metadata, PatchMetadata):
                continue
            if not isinstance(block.content, PatchContent):
                continue

            metadata = block.metadata
            content = block.content

            print(f"\n[BLOCK] Extracted: {metadata.id} (syntax: {block.syntax_name})")
            print(f"        File: {metadata.file}")
            print(f"        Start line: {metadata.start_line}")

            # Show extra metadata if present
            if hasattr(metadata, "author"):
                print(f"        Author: {metadata.author}")
            if hasattr(metadata, "priority"):
                print(f"        Priority: {metadata.priority}")

            # Show patch preview
            print("        Patch preview:")
            lines: list[str] = content.diff.strip().split("\\n")
            for line in lines[:3]:  # Show first 3 lines
                print(f"          {line}")
            if len(lines) > 3:
                print(f"          ... ({len(lines) - 3} more lines)")

        elif isinstance(event, BlockErrorEvent):
            # Block rejected
            reason = event.reason
            syntax = event.syntax
            print(f"\n[REJECT] {syntax} block rejected: {reason}")

    print("-" * 70)
    print(f"\nTotal blocks extracted: {len(blocks_extracted)}")

    # Summary
    print("\nBlock summary:")
    for i, block in enumerate(blocks_extracted, 1):
        # Type narrowing for summary
        from hother.streamblocks.blocks.patch import PatchMetadata

        if isinstance(block.metadata, PatchMetadata):
            syntax_display = block.syntax_name.replace("markdown_frontmatter_", "")
            print(f"  {i}. {block.metadata.id} - {block.metadata.file} ({syntax_display} syntax)")


if __name__ == "__main__":
    asyncio.run(main())
