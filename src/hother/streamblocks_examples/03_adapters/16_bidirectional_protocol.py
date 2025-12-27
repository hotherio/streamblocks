#!/usr/bin/env python3
"""Bidirectional protocol processing with input and output adapters."""

# --8<-- [start:imports]
import asyncio
from dataclasses import dataclass
from textwrap import dedent
from typing import Any

from hother.streamblocks import DelimiterFrontmatterSyntax, Registry
from hother.streamblocks.adapters.categories import EventCategory
from hother.streamblocks.core.protocol_processor import ProtocolStreamProcessor
from hother.streamblocks.core.types import BaseEvent, BlockEndEvent, TextDeltaEvent
from hother.streamblocks_examples.blocks.agent.files import FileOperations

# --8<-- [end:imports]


# --8<-- [start:custom_events]
@dataclass
class CustomInputEvent:
    """Custom input event format."""

    event_type: str  # "text", "metadata", "control"
    payload: str


@dataclass
class CustomOutputEvent:
    """Custom output event format."""

    kind: str  # "delta", "block", "other"
    data: Any


# --8<-- [end:custom_events]


# --8<-- [start:input_adapter]
class CustomInputAdapter:
    """Input adapter for custom event format."""

    def categorize(self, event: CustomInputEvent) -> EventCategory:
        """Categorize event for routing."""
        if event.event_type == "text":
            return EventCategory.TEXT_CONTENT
        if event.event_type == "metadata":
            return EventCategory.PASSTHROUGH
        return EventCategory.SKIP

    def extract_text(self, event: CustomInputEvent) -> str | None:
        """Extract text from text events."""
        return event.payload if event.event_type == "text" else None

    def get_metadata(self, event: CustomInputEvent) -> dict[str, Any] | None:
        """Extract metadata from events."""
        if event.event_type == "metadata":
            return {"source": event.payload}
        return None


# --8<-- [end:input_adapter]


# --8<-- [start:output_adapter]
class CustomOutputAdapter:
    """Output adapter for custom event format."""

    def to_protocol_event(self, event: BaseEvent) -> CustomOutputEvent | None:
        """Convert StreamBlocks events to custom format."""
        if isinstance(event, TextDeltaEvent):
            return CustomOutputEvent(kind="delta", data=event.delta)
        if isinstance(event, BlockEndEvent):
            block = event.get_block()
            if block:
                return CustomOutputEvent(
                    kind="block",
                    data={"id": block.metadata.id, "type": block.metadata.block_type},
                )
        return None

    def passthrough(self, original_event: Any) -> CustomOutputEvent | None:
        """Pass through non-text events."""
        if isinstance(original_event, CustomInputEvent):
            return CustomOutputEvent(kind="other", data=original_event.payload)
        return None


# --8<-- [end:output_adapter]


# --8<-- [start:main]
async def main() -> None:
    """Demonstrate bidirectional protocol processing."""
    # --8<-- [start:setup]
    syntax = DelimiterFrontmatterSyntax()
    registry = Registry(syntax=syntax)
    registry.register("files_operations", FileOperations)

    processor = ProtocolStreamProcessor[CustomInputEvent, CustomOutputEvent](
        registry,
        input_adapter=CustomInputAdapter(),
        output_adapter=CustomOutputAdapter(),
    )
    # --8<-- [end:setup]

    # --8<-- [start:stream]
    text = dedent("""
        !!start
        ---
        id: ops001
        block_type: files_operations
        ---
        src/main.py:C
        !!end
    """).strip()

    async def input_stream():
        # Mix of different event types
        yield CustomInputEvent("metadata", "session-123")
        yield CustomInputEvent("text", text)
        yield CustomInputEvent("control", "ping")  # Will be skipped

    print("=== Bidirectional Protocol ===")
    async for output_event in processor.process_stream(input_stream()):
        print(f"[{output_event.kind}] {output_event.data}")
    # --8<-- [end:stream]


# --8<-- [end:main]


if __name__ == "__main__":
    asyncio.run(main())
