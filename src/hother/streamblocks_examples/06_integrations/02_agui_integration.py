#!/usr/bin/env python3
"""AG-UI protocol integration for agent-to-frontend communication.

!!! note "Requires ag-ui package"
    Install with: pip install streamblocks[agui]
"""

# --8<-- [start:imports]
import asyncio
from textwrap import dedent

from hother.streamblocks import DelimiterFrontmatterSyntax, Registry
from hother.streamblocks.core.types import BlockEndEvent
from hother.streamblocks_examples.blocks.agent.files import FileOperations

# --8<-- [end:imports]


# --8<-- [start:main]
async def main() -> None:
    """Demonstrate AG-UI integration."""
    # Check if ag-ui is available
    try:
        from ag_ui.core import RunFinishedEvent, RunStartedEvent, TextMessageContentEvent

        from hother.streamblocks.extensions.agui import (
            AGUIEventFilter,
            create_agui_bidirectional_processor,
            create_agui_processor,
        )
    except ImportError:
        print("AG-UI package not installed.")
        print("Install with: pip install streamblocks[agui]")
        print("\nShowing available filter options instead:")
        show_filters()
        return

    syntax = DelimiterFrontmatterSyntax()
    registry = Registry(syntax=syntax)
    registry.register("files_operations", FileOperations)

    # --8<-- [start:unidirectional]
    # Mode 1: Unidirectional - AG-UI in, StreamBlocks events out
    print("=== Unidirectional (AG-UI → StreamBlocks) ===")
    processor = create_agui_processor(registry)

    text = dedent("""
        !!start
        ---
        id: ops001
        block_type: files_operations
        ---
        src/main.py:C
        !!end
    """).strip()

    async def agui_stream():
        yield RunStartedEvent(thread_id="thread-1", run_id="run-1")
        yield TextMessageContentEvent(delta=text, message_id="msg-1")
        yield RunFinishedEvent(thread_id="thread-1", run_id="run-1")

    async for event in processor.process_stream(agui_stream()):
        if isinstance(event, BlockEndEvent):
            block = event.get_block()
            if block:
                print("Block extracted:")
                print(block.model_dump_json(indent=2))
    # --8<-- [end:unidirectional]

    # --8<-- [start:bidirectional]
    # Mode 2: Bidirectional - AG-UI in, AG-UI out
    print("\n=== Bidirectional (AG-UI → AG-UI) ===")
    bidir_processor = create_agui_bidirectional_processor(
        registry,
        event_filter=AGUIEventFilter.BLOCKS_ONLY,
    )

    async def agui_stream2():
        yield RunStartedEvent(thread_id="thread-2", run_id="run-2")
        yield TextMessageContentEvent(delta=text, message_id="msg-2")
        yield RunFinishedEvent(thread_id="thread-2", run_id="run-2")

    async for event in bidir_processor.process_stream(agui_stream2()):
        if isinstance(event, dict):
            event_type = event.get("type", "unknown")
            if event_type == "CUSTOM":
                print(f"Custom event: {event.get('name')}")
            else:
                print(f"Passthrough: {event_type}")
    # --8<-- [end:bidirectional]


# --8<-- [end:main]


def show_filters() -> None:
    """Display available AG-UI event filters."""
    # --8<-- [start:filter_list]
    print("\nAGUIEventFilter options:")
    print("  ALL - Emit all StreamBlocks events")
    print("  BLOCKS_ONLY - Block lifecycle events only")
    print("  BLOCKS_WITH_PROGRESS - Block events + progress updates")
    print("  TEXT_AND_FINAL - Text streaming + final block results")
    print("\nCustom combinations:")
    print("  AGUIEventFilter.TEXT_DELTA | AGUIEventFilter.BLOCK_EXTRACTED")
    # --8<-- [end:filter_list]


if __name__ == "__main__":
    asyncio.run(main())
