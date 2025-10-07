"""Example demonstrating MarkdownFrontmatterSyntax with YAML frontmatter."""

import asyncio
from collections.abc import AsyncIterator

from hother.streamblocks import (
    BlockRegistry,
    EventType,
    MarkdownFrontmatterSyntax,
    StreamBlockProcessor,
)
from hother.streamblocks.content import PatchContent, PatchMetadata


async def example_stream() -> AsyncIterator[str]:
    """Example stream with markdown frontmatter blocks."""
    text = """
Here's a document with some patches using markdown-style blocks.

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

```yaml
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

```diff
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
"""

    # Chunk-based streaming (simulating real network transfer)
    chunk_size = 80  # Larger chunks for markdown blocks
    for i in range(0, len(text), chunk_size):
        chunk = text[i : i + chunk_size]
        yield chunk
        await asyncio.sleep(0.01)


async def main() -> None:
    """Main example function."""
    # Setup registry
    registry = BlockRegistry()

    # Register markdown syntaxes with different info strings
    # 1. Generic patch syntax
    patch_syntax = MarkdownFrontmatterSyntax(
        name="patch_syntax",
        metadata_class=PatchMetadata,
        content_class=PatchContent,
        fence="```",
        info_string="patch",
    )
    registry.register_syntax(patch_syntax, block_types=["patch"], priority=2)

    # 2. YAML-specific syntax
    yaml_syntax = MarkdownFrontmatterSyntax(
        name="yaml_syntax",
        metadata_class=PatchMetadata,
        content_class=PatchContent,
        fence="```",
        info_string="yaml",
    )
    registry.register_syntax(yaml_syntax, block_types=["patch"], priority=1)

    # 3. Diff-specific syntax
    diff_syntax = MarkdownFrontmatterSyntax(
        name="diff_syntax",
        metadata_class=PatchMetadata,
        content_class=PatchContent,
        fence="```",
        info_string="diff",
    )
    registry.register_syntax(diff_syntax, block_types=["patch"], priority=1)

    # Create processor
    processor = StreamBlockProcessor(registry, lines_buffer=10)

    # Process stream
    print("Processing markdown frontmatter blocks...")
    print("-" * 70)

    blocks_extracted = []
    current_partial = None

    async for event in processor.process_stream(example_stream()):
        if event.type == EventType.RAW_TEXT:
            # Raw text passed through
            if event.data.strip():
                print(f"[TEXT] {event.data.strip()}")

        elif event.type == EventType.BLOCK_DELTA:
            # Track partial block updates
            syntax = event.metadata["syntax"]
            section = event.metadata.get("section", "unknown")
            if current_partial != syntax:
                print(f"\n[DELTA] Started {syntax} block (section: {section})")
                current_partial = syntax
            # Only show section changes
            if "metadata_boundary" in str(event.metadata):
                print(f"[DELTA] Moved to {section} section")

        elif event.type == EventType.BLOCK_EXTRACTED:
            # Complete block extracted
            block = event.metadata["extracted_block"]
            blocks_extracted.append(block)
            current_partial = None

            print(f"\n[BLOCK] Extracted: {block.metadata.id} (syntax: {block.syntax_name})")
            print(f"        File: {block.metadata.file}")
            print(f"        Start line: {block.metadata.start_line}")

            # Show extra metadata if present
            if hasattr(block.metadata, "author"):
                print(f"        Author: {block.metadata.author}")
            if hasattr(block.metadata, "priority"):
                print(f"        Priority: {block.metadata.priority}")

            # Show patch preview
            print("        Patch preview:")
            lines = block.content.diff.strip().split("\\n")
            for line in lines[:3]:  # Show first 3 lines
                print(f"          {line}")
            if len(lines) > 3:
                print(f"          ... ({len(lines) - 3} more lines)")

        elif event.type == EventType.BLOCK_REJECTED:
            # Block rejected
            reason = event.metadata["reason"]
            syntax = event.metadata["syntax"]
            print(f"\n[REJECT] {syntax} block rejected: {reason}")

    print("-" * 70)
    print(f"\nTotal blocks extracted: {len(blocks_extracted)}")

    # Summary
    print("\nBlock summary:")
    for i, block in enumerate(blocks_extracted, 1):
        print(
            f"  {i}. {block.metadata.id} - {block.metadata.file} "
            f"({block.syntax_name.replace('markdown_frontmatter_', '')} syntax)"
        )


if __name__ == "__main__":
    asyncio.run(main())
