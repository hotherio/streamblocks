#!/usr/bin/env python3
"""Reject an artifact while it is still being written, and stop the stream."""

# --8<-- [start:imports]
import asyncio
from collections.abc import AsyncIterator

from hother.streamblocks import Registry, StreamBlockProcessor, XmlTagSyntax
from hother.streamblocks.blocks.artifacts import ARTIFACT_BLOCKS
from hother.streamblocks.core.processor import ProcessorConfig
from hother.streamblocks.core.types import BlockEndEvent, BlockErrorEvent
from hother.streamblocks.guards import forbid_patterns, max_lines, path_within

# --8<-- [end:imports]

RESPONSE = [
    "I'll write the module and then store the credentials.\n",
    '<artifact type="file" id="app" path="src/app.py">\n',
    "def run() -> None:\n",
    "    ...\n",
    "</artifact>\n",
    '<artifact type="file" id="env" path="../.env">\n',
    "API_KEY=sk-not-a-real-key\n",
    "DEBUG=1\n",
    "</artifact>\n",
    "All done.\n",
]


async def main() -> None:
    """Stop a simulated model as soon as it writes outside the project."""
    # --8<-- [start:setup]
    registry = Registry(syntax=XmlTagSyntax(), blocks=ARTIFACT_BLOCKS)
    # Guards run on every line of a block, starting with its opening line
    registry.add_stream_validator(path_within("src", "tests"))
    registry.add_stream_validator(max_lines(500))
    registry.add_stream_validator(forbid_patterns(r"(?i)api[_-]?key\s*="))

    # Stop processing at the first rejection and close the upstream stream
    processor = StreamBlockProcessor(registry, ProcessorConfig(abort_stream_on_failure=True))
    # --8<-- [end:setup]

    generated = 0

    async def model() -> AsyncIterator[str]:
        nonlocal generated
        for chunk in RESPONSE:
            generated += 1
            yield chunk

    # --8<-- [start:process]
    async for event in processor.process_stream(model()):
        if isinstance(event, BlockEndEvent):
            print(f"[done]    {event.metadata['path']}")
        elif isinstance(event, BlockErrorEvent):
            print(f"[aborted] {event.error_code}: {event.reason}")

    print(f"stream aborted: {processor.aborted}")
    # --8<-- [end:process]
    print(f"chunks generated: {generated} of {len(RESPONSE)}")

    opening_of_rejected_block = 6
    if not processor.aborted or generated != opening_of_rejected_block:
        msg = "the stream should stop at the opening line of the rejected block"
        raise RuntimeError(msg)


if __name__ == "__main__":
    asyncio.run(main())
