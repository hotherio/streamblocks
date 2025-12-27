"""Example demonstrating MarkdownFrontmatterSyntax with YAML frontmatter."""

import asyncio
from textwrap import dedent
from typing import TYPE_CHECKING

from hother.streamblocks import MarkdownFrontmatterSyntax, Registry, StreamBlockProcessor
from hother.streamblocks.core.processor import ProcessorConfig
from hother.streamblocks.core.types import (
    BlockContentDeltaEvent,
    BlockEndEvent,
    BlockErrorEvent,
    BlockHeaderDeltaEvent,
    BlockMetadataDeltaEvent,
    TextContentEvent,
)
from hother.streamblocks_examples.blocks.agent.patch import Patch
from hother.streamblocks_examples.helpers.simulator import simulated_stream

if TYPE_CHECKING:
    from hother.streamblocks.core.models import ExtractedBlock
    from hother.streamblocks.core.types import BaseContent, BaseMetadata


async def main() -> None:
    """Main example function."""
    # Create markdown frontmatter syntax for patch blocks
    # Each Registry holds exactly one syntax.
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
    config = ProcessorConfig(lines_buffer=10)
    processor = StreamBlockProcessor(registry, config=config)

    # Example text with markdown frontmatter blocks
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

    # Process stream
    print("Processing markdown frontmatter blocks...")
    print("-" * 70)

    blocks_extracted: list[ExtractedBlock[BaseMetadata, BaseContent]] = []
    current_partial = None

    async for event in processor.process_stream(simulated_stream(text)):
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
            print("\n[BLOCK] Extracted:")
            print(block.model_dump_json(indent=2))

        elif isinstance(event, BlockErrorEvent):
            # Block rejected
            reason = event.reason
            syntax = event.syntax
            print(f"\n[REJECT] {syntax} block rejected: {reason}")

    print("-" * 70)
    print(f"\nTotal blocks extracted: {len(blocks_extracted)}")

    # Show all extracted blocks
    print("\nExtracted blocks (full details):")
    for i, block in enumerate(blocks_extracted, 1):
        print(f"\n--- Block {i} ---")
        print(block.model_dump_json(indent=2))


if __name__ == "__main__":
    asyncio.run(main())
