"""Example demonstrating DelimiterPreambleSyntax with inline metadata.

This syntax uses a compact inline format where metadata is embedded in the opening delimiter.
Perfect for simple use cases where you don't need extensive metadata.
"""

import asyncio
from collections.abc import AsyncIterator
from typing import Literal

from pydantic import Field

from hother.streamblocks import DelimiterPreambleSyntax, EventType, Registry, StreamBlockProcessor
from hother.streamblocks.core.models import Block, ExtractedBlock
from hother.streamblocks.core.types import BaseContent, BaseMetadata


# Custom content models for this example
class CommandMetadata(BaseMetadata):
    """Metadata for command blocks."""

    id: str
    block_type: Literal["command"] = "command"  # type: ignore[assignment]
    # DelimiterPreambleSyntax can also capture inline parameters as param_0, param_1, etc.


class CommandContent(BaseContent):
    """Content for command blocks - simple shell commands."""

    commands: list[str] = Field(default_factory=list)

    @classmethod
    def parse(cls, raw_text: str) -> "CommandContent":
        """Parse command content from raw text."""
        lines = raw_text.strip().split("\n")
        commands = [line.strip() for line in lines if line.strip()]
        return cls(raw_content=raw_text, commands=commands)


# Create the block type
CommandBlock = Block[CommandMetadata, CommandContent]


async def example_stream() -> AsyncIterator[str]:
    """Example stream with delimiter preamble blocks."""
    text = """
Let's run some shell commands using the compact inline syntax.

!!cmd01:command
ls -la
pwd
echo "Hello, World!"
!!end

Here's another command block with inline parameters.
The inline parameter can be accessed as param_0 in metadata.

!!cmd02:command:high-priority
git status
git diff
!!end

You can have multiple inline parameters separated by colons:

!!cmd03:command:urgent:production
docker ps
docker logs app
!!end

Some text between blocks.

!!cmd04:command
npm install
npm run build
npm test
!!end

That's all for the commands!
"""

    # Simulate streaming
    chunk_size = 60
    for i in range(0, len(text), chunk_size):
        chunk = text[i : i + chunk_size]
        yield chunk
        await asyncio.sleep(0.01)


async def main() -> None:
    """Main example function."""
    print("=== DelimiterPreambleSyntax Example ===\n")
    print("Compact inline format: !!<id>:<type>[:<param1>:<param2>...]")
    print("Perfect for simple use cases with minimal metadata.\n")

    # Create delimiter preamble syntax
    # Uses !! delimiter with inline metadata: !!id:type[:params]
    syntax = DelimiterPreambleSyntax(delimiter="!!")

    # Create type-specific registry and register block
    registry = Registry(syntax=syntax)
    registry.register("command", CommandBlock)

    # Add a simple validator
    def no_rm_commands(block: ExtractedBlock[CommandMetadata, CommandContent]) -> bool:
        """Don't allow dangerous rm commands."""
        return not any("rm -rf" in cmd for cmd in block.content.commands)

    registry.add_validator("command", no_rm_commands)

    # Create processor
    processor = StreamBlockProcessor(registry, lines_buffer=5)

    # Process stream
    print("Processing command blocks...\n")

    blocks_extracted: list[ExtractedBlock[CommandMetadata, CommandContent]] = []

    async for event in processor.process_stream(example_stream()):
        if event.type == EventType.RAW_TEXT:
            # Raw text passed through
            if event.data.strip():
                text = event.data.strip()
                if len(text) > 60:
                    text = text[:57] + "..."
                print(f"[TEXT] {text}")

        elif event.type == EventType.BLOCK_EXTRACTED:
            # Complete block extracted
            block = event.block
            blocks_extracted.append(block)

            # Type narrow to CommandMetadata and CommandContent for specific access
            if isinstance(block.metadata, CommandMetadata) and isinstance(block.content, CommandContent):
                metadata = block.metadata
                content = block.content

                print(f"\n{'=' * 60}")
                print(f"[COMMAND BLOCK] {metadata.id}")

                # Show inline parameters if present
                inline_params = []
                i = 0
                while hasattr(metadata, f"param_{i}"):
                    inline_params.append(getattr(metadata, f"param_{i}"))
                    i += 1

                if inline_params:
                    print(f"                Inline params: {', '.join(inline_params)}")

                print(f"                Commands ({len(content.commands)}):")
                for cmd in content.commands:
                    print(f"                  $ {cmd}")
                print("=" * 60)

        elif event.type == EventType.BLOCK_REJECTED:
            # Block rejected
            print(f"\n[REJECT] {event.reason}")

    print("\n\nEXTRACTED BLOCKS SUMMARY:")
    print(f"Total blocks: {len(blocks_extracted)}")
    print("\nCommand blocks:")
    for cmd_block in blocks_extracted:
        if isinstance(cmd_block.metadata, CommandMetadata) and isinstance(cmd_block.content, CommandContent):
            # Check for inline params
            params_str = ""
            if hasattr(cmd_block.metadata, "param_0"):
                params = []
                i = 0
                while hasattr(cmd_block.metadata, f"param_{i}"):
                    params.append(getattr(cmd_block.metadata, f"param_{i}"))
                    i += 1
                params_str = f" [{', '.join(params)}]"

            print(f"  - {cmd_block.metadata.id}{params_str}: {len(cmd_block.content.commands)} commands")

    print("\n✓ DelimiterPreambleSyntax processing complete!")
    print("\nKey benefits:")
    print("  • Compact inline format")
    print("  • Minimal syntax overhead")
    print("  • Perfect for simple use cases")
    print("  • Supports inline parameters")


if __name__ == "__main__":
    asyncio.run(main())
