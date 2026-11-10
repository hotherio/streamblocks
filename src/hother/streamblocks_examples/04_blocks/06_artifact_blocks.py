#!/usr/bin/env python3
"""Stream file and patch artifacts written inside prose, using the XML tag syntax."""

# --8<-- [start:imports]
import asyncio
from textwrap import dedent

from hother.streamblocks import Registry, StreamBlockProcessor, XmlTagSyntax
from hother.streamblocks.blocks.artifacts import ARTIFACT_BLOCKS, FILE_BLOCK_TYPE, PATCH_BLOCK_TYPE
from hother.streamblocks.core.types import BlockContentDeltaEvent, BlockEndEvent, BlockStartEvent, TextContentEvent
from hother.streamblocks_examples.helpers.simulator import chunked_text_stream

# --8<-- [end:imports]

RESPONSE = dedent("""\
    Sure, here is a small greeter and then a tweak to it.

    <artifact type="file" id="greeter" path="src/greeter.py" language="python">
    def greet(name: str) -> str:
        return f"hello {name}"
    </artifact>

    Now let's make the greeting friendlier:

    <artifact type="patch" id="friendlier" path="src/greeter.py">
    <<<<<<< SEARCH
        return f"hello {name}"
    =======
        return f"Hello, {name}!"
    >>>>>>> REPLACE
    </artifact>

    That is all.
    """)


async def main() -> None:
    """Extract artifacts as they stream and apply them to an in-memory project."""
    # --8<-- [start:setup]
    # One registry: the tag syntax plus the built-in file, patch and document blocks
    registry = Registry(syntax=XmlTagSyntax(), blocks=ARTIFACT_BLOCKS)
    processor = StreamBlockProcessor(registry)
    # --8<-- [end:setup]

    # The same registry documents the format for the model
    print(registry.to_prompt().splitlines()[0])

    project: dict[str, str] = {}

    # --8<-- [start:process]
    async for event in processor.process_stream(chunked_text_stream(RESPONSE, chunk_size=24)):
        if isinstance(event, TextContentEvent) and event.content.strip():
            print(f"[text]  {event.content}")
        elif isinstance(event, BlockStartEvent):
            print(f"[start] {event.inline_metadata}")
        elif isinstance(event, BlockContentDeltaEvent):
            print(f"        | {event.delta}")
        elif isinstance(event, BlockEndEvent):
            block = event.get_block()
            if block is None:
                continue
            path = block.metadata.path
            if event.block_type == FILE_BLOCK_TYPE:
                project[path] = block.content.raw_content
            elif event.block_type == PATCH_BLOCK_TYPE:
                project[path] = block.content.apply(project[path])
            print(f"[done]  {event.block_type} -> {path}")
    # --8<-- [end:process]

    print("\nProject after the stream:")
    for path, text in project.items():
        print(f"--- {path}\n{text}")

    expected = 'def greet(name: str) -> str:\n    return f"Hello, {name}!"'
    if project.get("src/greeter.py") != expected:
        msg = "artifacts were not extracted and applied as expected"
        raise RuntimeError(msg)


if __name__ == "__main__":
    asyncio.run(main())
