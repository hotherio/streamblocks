"""Example demonstrating multiple syntax types in a single stream."""

import asyncio
from typing import AsyncIterator

from streamblocks import (
    BlockRegistry,
    DelimiterFrontmatterSyntax,
    DelimiterPreambleSyntax,
    EventType,
    MarkdownFrontmatterSyntax,
    StreamBlockProcessor,
)
from streamblocks.content import (
    FileOperationsContent,
    FileOperationsMetadata,
    PatchContent,
    PatchMetadata,
)


async def example_stream() -> AsyncIterator[str]:
    """Example stream mixing all three syntax types."""
    text = """
In this document, we'll demonstrate how StreamBlocks can handle multiple
syntax types simultaneously in the same stream.

First, let's create some files using delimiter preamble syntax:

!!files01:files_operations
README.md:C
docs/getting-started.md:C
docs/api-reference.md:C
src/__init__.py:C
!!end

Now, let's use markdown frontmatter to define a patch:

```patch
---
id: readme-update
block_type: patch
file: README.md
start_line: 1
---
 # My Project
+
+## Installation
+
+```bash
+pip install myproject
+```
+
 ## Overview
```

Here's another way using delimiter frontmatter:

!!start
---
id: patch-002
block_type: patch
file: src/main.py
start_line: 10
---
-def old_function():
-    return "deprecated"
+def new_function():
+    return "modern"
!!end

Let's clean up some old files:

!!cleanup01:files_operations:critical
old_module.py:D
deprecated.py:D
legacy_tests.py:D
!!end

And add configuration using markdown style:

```yaml
---
id: config-patch
block_type: patch
file: config.yaml
start_line: 5
---
 settings:
   debug: false
+  cache: true
+  timeout: 30
```

Finally, let's use delimiter frontmatter for a complex patch:

!!start
---
id: feature-patch
block_type: patch
file: features.py
start_line: 50
author: dev-team
tags: [feature, api, v2]
---
+class NewFeature:
+    \"\"\"Awesome new feature.\"\"\"
+    
+    def __init__(self, config):
+        self.config = config
+    
+    def process(self, data):
+        # Implementation here
+        return data
!!end

That's it! We've successfully mixed all three syntax types.
"""

    # Simulate realistic streaming with varying chunk sizes
    chunk_patterns = [30, 45, 60, 40, 55, 35, 50, 65, 42, 58, 38, 48, 62, 36, 52, 46, 56, 34, 44, 68]

    i = 0
    pattern_idx = 0

    while i < len(text):
        chunk_size = chunk_patterns[pattern_idx % len(chunk_patterns)]
        chunk = text[i : i + chunk_size]
        yield chunk
        i += chunk_size
        pattern_idx += 1
        await asyncio.sleep(0.008)  # Slightly faster streaming


async def main() -> None:
    """Main example function."""
    # Setup registry
    registry = BlockRegistry()

    # Register all three syntax types

    # 1. Delimiter preamble for file operations
    file_ops_syntax = DelimiterPreambleSyntax(
        metadata_class=FileOperationsMetadata,
        content_class=FileOperationsContent,
    )
    registry.register_syntax(
        file_ops_syntax,
        block_types=["files_operations"],
        priority=3,  # Highest priority
    )

    # 2. Markdown frontmatter for patches
    md_patch_syntax = MarkdownFrontmatterSyntax(
        metadata_class=PatchMetadata,
        content_class=PatchContent,
        fence="```",
        info_string="patch",
    )
    registry.register_syntax(md_patch_syntax, block_types=["patch"], priority=2)

    # Also register YAML info string for patches
    yaml_patch_syntax = MarkdownFrontmatterSyntax(
        metadata_class=PatchMetadata,
        content_class=PatchContent,
        fence="```",
        info_string="yaml",
    )
    registry.register_syntax(yaml_patch_syntax, block_types=["patch"], priority=2)

    # 3. Delimiter frontmatter as a fallback for patches
    delim_patch_syntax = DelimiterFrontmatterSyntax(
        metadata_class=PatchMetadata,
        content_class=PatchContent,
    )
    registry.register_syntax(
        delim_patch_syntax,
        block_types=["patch"],
        priority=1,  # Lower priority
    )

    # Add a validator for critical operations
    def validate_critical_ops(metadata: FileOperationsMetadata, content: FileOperationsContent) -> bool:
        """Extra validation for critical operations."""
        if hasattr(metadata, "param_0") and metadata.param_0 == "critical":
            # Don't allow deleting system files in critical ops
            for op in content.operations:
                if op.action == "delete" and op.path.startswith("/"):
                    return False
        return True

    registry.add_validator("files_operations", validate_critical_ops)

    # Create processor with larger buffer for complex streams
    processor = StreamBlockProcessor(registry, lines_buffer=10)

    # Process stream
    print("Processing mixed syntax stream...")
    print("=" * 80)

    # Track statistics
    stats = {
        "raw_text_lines": 0,
        "blocks_by_syntax": {},
        "blocks_by_type": {},
        "total_blocks": 0,
    }

    async for event in processor.process_stream(example_stream()):
        if event.type == EventType.RAW_TEXT:
            # Count raw text lines
            if event.data.strip():
                stats["raw_text_lines"] += 1
                # Only show first 60 chars of text lines
                text = event.data.strip()
                if len(text) > 60:
                    text = text[:57] + "..."
                print(f"[TEXT] {text}")

        elif event.type == EventType.BLOCK_DELTA:
            # Don't show all deltas to reduce noise
            pass

        elif event.type == EventType.BLOCK_EXTRACTED:
            # Complete block extracted
            block = event.metadata["extracted_block"]
            stats["total_blocks"] += 1

            # Update syntax stats
            syntax_key = block.syntax_name.split("_")[0]  # Get base syntax type
            stats["blocks_by_syntax"][syntax_key] = stats["blocks_by_syntax"].get(syntax_key, 0) + 1

            # Update type stats
            block_type = block.metadata.block_type
            stats["blocks_by_type"][block_type] = stats["blocks_by_type"].get(block_type, 0) + 1

            print(f"\n{'='*60}")
            print(f"[BLOCK] {block.metadata.id} ({block.metadata.block_type})")
            print(f"        Syntax: {block.syntax_name}")

            if block_type == "files_operations":
                print(f"        Operations: {len(block.content.operations)}")
                for op in block.content.operations[:3]:  # Show first 3
                    print(f"          - {op.action}: {op.path}")
                if len(block.content.operations) > 3:
                    print(f"          ... and {len(block.content.operations) - 3} more")
                # Check for extra params
                if hasattr(block.metadata, "param_0"):
                    print(f"        Priority: {block.metadata.param_0}")

            elif block_type == "patch":
                print(f"        File: {block.metadata.file}")
                print(f"        Start line: {block.metadata.start_line}")
                if hasattr(block.metadata, "author"):
                    print(f"        Author: {block.metadata.author}")
                if hasattr(block.metadata, "tags"):
                    print(f"        Tags: {', '.join(block.metadata.tags)}")
                # Show patch stats
                lines = block.content.diff.strip().split("\\n")
                additions = sum(1 for l in lines if l.startswith("+"))
                deletions = sum(1 for l in lines if l.startswith("-"))
                print(f"        Changes: +{additions} -{deletions}")

        elif event.type == EventType.BLOCK_REJECTED:
            # Block rejected
            reason = event.metadata["reason"]
            syntax = event.metadata["syntax"]
            print(f"\n[REJECT] {syntax}: {reason}")

    # Print summary statistics
    print("\n" + "=" * 80)
    print("\nSTREAM PROCESSING SUMMARY:")
    print(f"  Raw text lines: {stats['raw_text_lines']}")
    print(f"  Total blocks extracted: {stats['total_blocks']}")

    print("\n  Blocks by syntax type:")
    for syntax, count in sorted(stats["blocks_by_syntax"].items()):
        print(f"    - {syntax}: {count}")

    print("\n  Blocks by content type:")
    for block_type, count in sorted(stats["blocks_by_type"].items()):
        print(f"    - {block_type}: {count}")

    print("\n✓ Successfully demonstrated mixed syntax processing!")


if __name__ == "__main__":
    asyncio.run(main())
