"""Example demonstrating MarkdownFrontmatterSyntax with YAML frontmatter.

This example shows how to use markdown code blocks with simple content
that DON'T require custom parsing. Perfect for beginners learning the syntax format.
"""

import asyncio
from collections.abc import AsyncIterator
from typing import Literal

from pydantic import Field

from hother.streamblocks import EventType, MarkdownFrontmatterSyntax, Registry, StreamBlockProcessor
from hother.streamblocks.core.models import Block, ExtractedBlock
from hother.streamblocks.core.types import BaseContent, BaseMetadata


# Simple content models - NO custom parse() needed!
class CodeSnippetMetadata(BaseMetadata):
    """Metadata for code snippet blocks."""

    id: str
    block_type: Literal["code_snippet"] = "code_snippet"  # type: ignore[assignment]
    language: str = "text"
    filename: str | None = None
    description: str | None = None
    tags: list[str] = Field(default_factory=list)


class CodeSnippetContent(BaseContent):
    """Content for code snippet blocks.

    Uses the default parse() method - just stores raw_content.
    No custom parsing needed!
    """

    # Inherits raw_content field from BaseContent
    # No custom parse() method - uses default implementation


# Create the block type
CodeSnippetBlock = Block[CodeSnippetMetadata, CodeSnippetContent]


async def example_stream() -> AsyncIterator[str]:
    """Example stream with markdown frontmatter blocks."""
    text = """
Here's a document with code snippets using markdown-style blocks with YAML frontmatter.

```python
---
id: snippet-001
block_type: code_snippet
language: python
filename: hello.py
description: Simple hello world function
tags:
  - tutorial
  - basics
---
def hello_world():
    \"\"\"Print a friendly greeting.\"\"\"
    print("Hello, World!")
    return True
```

Now let's add a JavaScript snippet:

```javascript
---
id: snippet-002
block_type: code_snippet
language: javascript
filename: utils.js
description: Utility functions
---
function capitalize(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

function sum(a, b) {
    return a + b;
}
```

Here's a configuration file snippet:

```yaml
---
id: snippet-003
block_type: code_snippet
language: yaml
filename: config.yaml
tags:
  - configuration
  - deployment
---
app:
  name: myapp
  version: 1.0.0
  environment: production

database:
  host: localhost
  port: 5432
  name: mydb
```

And finally, some SQL:

```sql
---
id: snippet-004
block_type: code_snippet
language: sql
description: User queries
tags:
  - database
  - query
---
SELECT id, username, email
FROM users
WHERE active = true
ORDER BY created_at DESC
LIMIT 10;
```

That's all for the code snippets!
"""

    # Chunk-based streaming (simulating real network transfer)
    chunk_size = 80  # Larger chunks for markdown blocks
    for i in range(0, len(text), chunk_size):
        chunk = text[i : i + chunk_size]
        yield chunk
        await asyncio.sleep(0.01)


async def main() -> None:
    """Main example function."""
    print("=== MarkdownFrontmatterSyntax Example ===\n")
    print("This example uses SIMPLE blocks with NO custom parsing.")
    print("Content is stored directly in the raw_content field.\n")

    # Create markdown frontmatter syntax for code snippets
    # Note: In the new API, each Registry holds exactly one syntax.
    # To handle multiple info strings, you would need separate processors
    syntax = MarkdownFrontmatterSyntax(
        fence="```",
        info_string="",  # Empty = match any code block
    )

    # Create type-specific registry and register block
    registry = Registry(syntax=syntax)
    registry.register("code_snippet", CodeSnippetBlock)

    # Create processor
    processor = StreamBlockProcessor(registry, lines_buffer=10)

    # Process stream
    print("Processing code snippet blocks...\n")

    blocks_extracted: list[ExtractedBlock[BaseMetadata, BaseContent]] = []
    current_partial = None

    async for event in processor.process_stream(example_stream()):
        if event.type == EventType.RAW_TEXT:
            # Raw text passed through
            if event.data.strip():
                text = event.data.strip()
                if len(text) > 60:
                    text = text[:57] + "..."
                print(f"[TEXT] {text}")

        elif event.type == EventType.BLOCK_DELTA:
            # Track partial block updates
            syntax_name = event.syntax
            section = event.section
            if current_partial != syntax_name:
                print(f"\n[DELTA] Started {syntax_name} block (section: {section})")
                current_partial = syntax_name

        elif event.type == EventType.BLOCK_EXTRACTED:
            # Complete block extracted
            block = event.block
            blocks_extracted.append(block)
            current_partial = None

            # Type narrowing for code snippet blocks
            if isinstance(block.metadata, CodeSnippetMetadata) and isinstance(
                block.content, CodeSnippetContent
            ):
                metadata = block.metadata
                content = block.content

                print(f"\n{'=' * 60}")
                print(f"[CODE SNIPPET] {metadata.id}")
                print(f"               Language: {metadata.language}")
                if metadata.filename:
                    print(f"               File: {metadata.filename}")
                if metadata.description:
                    print(f"               Description: {metadata.description}")
                if metadata.tags:
                    print(f"               Tags: {', '.join(metadata.tags)}")

                # Access raw_content directly - no parsing needed!
                print(f"\n               Code ({len(content.raw_content)} chars):")
                lines = content.raw_content.strip().split("\n")
                for line in lines[:5]:  # Show first 5 lines
                    print(f"               {line}")
                if len(lines) > 5:
                    print(f"               ... ({len(lines) - 5} more lines)")
                print("=" * 60)

        elif event.type == EventType.BLOCK_REJECTED:
            # Block rejected
            reason = event.reason
            syntax_name = event.syntax
            print(f"\n[REJECT] {syntax_name} block rejected: {reason}")

    print("\n\nEXTRACTED BLOCKS SUMMARY:")
    print(f"Total blocks: {len(blocks_extracted)}")

    # Summary
    print("\nCode snippets:")
    for i, block in enumerate(blocks_extracted, 1):
        # Type narrowing for summary
        if isinstance(block.metadata, CodeSnippetMetadata):
            filename = f" ({block.metadata.filename})" if block.metadata.filename else ""
            print(f"  {i}. {block.metadata.language}{filename} - {block.metadata.id}")

    print("\n" + "=" * 60)
    print("KEY POINTS:")
    print("=" * 60)
    print("✓ No custom parse() method needed")
    print("✓ Content stored directly in raw_content field")
    print("✓ Perfect for code snippets (use as-is)")
    print("✓ Markdown-compatible (renders in editors)")
    print("✓ Metadata in YAML frontmatter (rich structure)")
    print("✓ Syntax highlighting in most editors")
    print("\n✓ MarkdownFrontmatterSyntax processing complete!")


if __name__ == "__main__":
    asyncio.run(main())
