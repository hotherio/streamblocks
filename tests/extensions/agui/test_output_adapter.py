"""Tests for AG-UI output adapter."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from hother.streamblocks.core.types import (
    BlockContentDeltaEvent,
    BlockEndEvent,
    BlockErrorEvent,
    BlockHeaderDeltaEvent,
    BlockMetadataDeltaEvent,
    BlockStartEvent,
    EventType,
    TextContentEvent,
    TextDeltaEvent,
)
from hother.streamblocks.extensions.agui.filters import AGUIEventFilter
from hother.streamblocks.extensions.agui.output_adapter import AGUIOutputAdapter


class TestAGUIOutputAdapterInit:
    """Tests for AGUIOutputAdapter initialization."""

    def test_default_filter_is_all(self) -> None:
        """Test that default filter is ALL."""
        adapter = AGUIOutputAdapter()

        assert adapter.event_filter == AGUIEventFilter.ALL

    def test_custom_filter(self) -> None:
        """Test initialization with custom filter."""
        adapter = AGUIOutputAdapter(event_filter=AGUIEventFilter.BLOCKS_ONLY)

        assert adapter.event_filter == AGUIEventFilter.BLOCKS_ONLY

    def test_message_id_starts_none(self) -> None:
        """Test that message ID starts as None."""
        adapter = AGUIOutputAdapter()

        assert adapter._message_id is None


class TestAGUIOutputAdapterToProtocolEvent:
    """Tests for AGUIOutputAdapter.to_protocol_event()."""

    def test_text_delta_event(self) -> None:
        """Test converting TextDeltaEvent to AG-UI format."""
        adapter = AGUIOutputAdapter()
        event = TextDeltaEvent(delta="Hello")

        result = adapter.to_protocol_event(event)

        assert result is not None
        assert result["type"] == "TEXT_MESSAGE_CONTENT"
        assert result["delta"] == "Hello"
        assert "message_id" in result

    def test_text_content_event(self) -> None:
        """Test converting TextContentEvent to AG-UI format."""
        adapter = AGUIOutputAdapter()
        event = TextContentEvent(content="Line content", line_number=1)

        result = adapter.to_protocol_event(event)

        assert result is not None
        assert result["type"] == "TEXT_MESSAGE_CONTENT"
        assert result["delta"] == "Line content"
        assert "message_id" in result

    def test_block_start_event(self) -> None:
        """Test converting BlockStartEvent to AG-UI format."""
        adapter = AGUIOutputAdapter()
        event = BlockStartEvent(
            block_id="block-1",
            syntax="markdown",
            start_line=5,
            inline_metadata={"key": "value"},
        )

        result = adapter.to_protocol_event(event)

        assert result is not None
        assert result["type"] == "CUSTOM"
        assert result["name"] == "streamblocks.block_start"
        assert result["value"]["block_id"] == "block-1"
        assert result["value"]["syntax"] == "markdown"
        assert result["value"]["start_line"] == 5
        assert result["value"]["inline_metadata"] == {"key": "value"}

    def test_block_header_delta_event(self) -> None:
        """Test converting BlockHeaderDeltaEvent to AG-UI format."""
        adapter = AGUIOutputAdapter()
        event = BlockHeaderDeltaEvent(
            block_id="block-1",
            syntax="delimiter",
            delta="header text",
            current_line=10,
            accumulated_size=100,
        )

        result = adapter.to_protocol_event(event)

        assert result is not None
        assert result["type"] == "CUSTOM"
        assert result["name"] == "streamblocks.block_delta"
        assert result["value"]["block_id"] == "block-1"
        assert result["value"]["section"] == "header"
        assert result["value"]["delta"] == "header text"

    def test_block_metadata_delta_event(self) -> None:
        """Test converting BlockMetadataDeltaEvent to AG-UI format."""
        adapter = AGUIOutputAdapter()
        event = BlockMetadataDeltaEvent(
            block_id="block-1",
            syntax="frontmatter",
            delta="id: test",
            current_line=2,
            accumulated_size=50,
        )

        result = adapter.to_protocol_event(event)

        assert result is not None
        assert result["type"] == "CUSTOM"
        assert result["name"] == "streamblocks.block_delta"
        assert result["value"]["section"] == "metadata"

    def test_block_content_delta_event(self) -> None:
        """Test converting BlockContentDeltaEvent to AG-UI format."""
        adapter = AGUIOutputAdapter()
        event = BlockContentDeltaEvent(
            block_id="block-1",
            syntax="fenced",
            delta="content line",
            current_line=15,
            accumulated_size=200,
        )

        result = adapter.to_protocol_event(event)

        assert result is not None
        assert result["type"] == "CUSTOM"
        assert result["name"] == "streamblocks.block_delta"
        assert result["value"]["section"] == "content"

    def test_block_end_event(self) -> None:
        """Test converting BlockEndEvent to AG-UI format."""
        adapter = AGUIOutputAdapter()
        event = BlockEndEvent(
            block_id="block-1",
            block_type="code",
            syntax="markdown",
            start_line=1,
            end_line=10,
            metadata={"id": "test"},
            content={"raw_content": "content"},
            raw_content="full raw content",
            hash_id="abc123",
        )

        result = adapter.to_protocol_event(event)

        assert result is not None
        assert result["type"] == "CUSTOM"
        assert result["name"] == "streamblocks.block_end"
        assert result["value"]["block_id"] == "block-1"
        assert result["value"]["block_type"] == "code"
        assert result["value"]["hash_id"] == "abc123"

    def test_block_error_event(self) -> None:
        """Test converting BlockErrorEvent to AG-UI format."""
        adapter = AGUIOutputAdapter()
        event = BlockErrorEvent(
            block_id="block-1",
            reason="Validation failed",
            syntax="delimiter",
            start_line=1,
            end_line=5,
        )

        result = adapter.to_protocol_event(event)

        assert result is not None
        assert result["type"] == "CUSTOM"
        assert result["name"] == "streamblocks.block_error"
        assert result["value"]["block_id"] == "block-1"
        assert result["value"]["reason"] == "Validation failed"

    def test_unknown_event_returns_none(self) -> None:
        """Test that unknown events return None."""
        adapter = AGUIOutputAdapter()
        # Create a mock event that doesn't match any known type
        mock_event = MagicMock()
        mock_event.type = EventType.STREAM_STARTED

        result = adapter.to_protocol_event(mock_event)

        assert result is None


class TestAGUIOutputAdapterFiltering:
    """Tests for event filtering with AGUIOutputAdapter."""

    def test_filter_blocks_text_delta(self) -> None:
        """Test that BLOCKS_ONLY filter blocks TextDeltaEvent."""
        adapter = AGUIOutputAdapter(event_filter=AGUIEventFilter.BLOCKS_ONLY)
        event = TextDeltaEvent(delta="text")

        result = adapter.to_protocol_event(event)

        assert result is None

    def test_filter_blocks_text_content(self) -> None:
        """Test that filter without RAW_TEXT blocks TextContentEvent."""
        adapter = AGUIOutputAdapter(event_filter=AGUIEventFilter.BLOCKS_ONLY)
        event = TextContentEvent(content="line", line_number=1)

        result = adapter.to_protocol_event(event)

        assert result is None

    def test_filter_blocks_block_opened(self) -> None:
        """Test that TEXT_AND_FINAL filter blocks BlockStartEvent."""
        adapter = AGUIOutputAdapter(event_filter=AGUIEventFilter.TEXT_AND_FINAL)
        event = BlockStartEvent(
            block_id="b1",
            syntax="md",
            start_line=1,
        )

        result = adapter.to_protocol_event(event)

        assert result is None

    def test_filter_blocks_block_delta(self) -> None:
        """Test that BLOCKS_ONLY filter blocks delta events."""
        adapter = AGUIOutputAdapter(event_filter=AGUIEventFilter.BLOCKS_ONLY)
        event = BlockHeaderDeltaEvent(
            block_id="b1",
            syntax="md",
            delta="d",
            current_line=1,
            accumulated_size=1,
        )

        result = adapter.to_protocol_event(event)

        assert result is None

    def test_filter_allows_block_end(self) -> None:
        """Test that BLOCKS_ONLY filter allows BlockEndEvent."""
        adapter = AGUIOutputAdapter(event_filter=AGUIEventFilter.BLOCKS_ONLY)
        event = BlockEndEvent(
            block_id="b1",
            block_type="code",
            syntax="md",
            start_line=1,
            end_line=5,
            metadata={},
            content={},
            raw_content="",
            hash_id="hash",
        )

        result = adapter.to_protocol_event(event)

        assert result is not None

    def test_filter_allows_block_error(self) -> None:
        """Test that BLOCKS_ONLY filter allows BlockErrorEvent."""
        adapter = AGUIOutputAdapter(event_filter=AGUIEventFilter.BLOCKS_ONLY)
        event = BlockErrorEvent(
            block_id="b1",
            reason="error",
            syntax="md",
            start_line=1,
        )

        result = adapter.to_protocol_event(event)

        assert result is not None

    def test_blocks_with_progress_allows_deltas(self) -> None:
        """Test that BLOCKS_WITH_PROGRESS allows delta events."""
        adapter = AGUIOutputAdapter(event_filter=AGUIEventFilter.BLOCKS_WITH_PROGRESS)
        event = BlockContentDeltaEvent(
            block_id="b1",
            syntax="md",
            delta="content",
            current_line=5,
            accumulated_size=50,
        )

        result = adapter.to_protocol_event(event)

        assert result is not None

    def test_text_and_final_allows_text_delta(self) -> None:
        """Test that TEXT_AND_FINAL allows TextDeltaEvent."""
        adapter = AGUIOutputAdapter(event_filter=AGUIEventFilter.TEXT_AND_FINAL)
        event = TextDeltaEvent(delta="text")

        result = adapter.to_protocol_event(event)

        assert result is not None

    def test_none_filter_blocks_all(self) -> None:
        """Test that NONE filter blocks all events."""
        adapter = AGUIOutputAdapter(event_filter=AGUIEventFilter.NONE)

        events = [
            TextDeltaEvent(delta="t"),
            TextContentEvent(content="c", line_number=1),
            BlockStartEvent(block_id="b", syntax="s", start_line=1),
            BlockEndEvent(
                block_id="b",
                block_type="t",
                syntax="s",
                start_line=1,
                end_line=2,
                metadata={},
                content={},
                raw_content="",
                hash_id="h",
            ),
        ]

        for event in events:
            result = adapter.to_protocol_event(event)
            assert result is None


class TestAGUIOutputAdapterPassthrough:
    """Tests for AGUIOutputAdapter.passthrough()."""

    def test_passthrough_dict_with_type(self) -> None:
        """Test passthrough of dict event with type field."""
        adapter = AGUIOutputAdapter()
        original = {"type": "RUN_STARTED", "data": "value"}

        result = adapter.passthrough(original)

        assert result is original

    def test_passthrough_object_with_type(self) -> None:
        """Test passthrough of object with type attribute."""
        adapter = AGUIOutputAdapter()
        original = MagicMock()
        original.type = "TEXT_MESSAGE_CONTENT"

        result = adapter.passthrough(original)

        assert result is original

    def test_passthrough_wraps_other_events(self) -> None:
        """Test that other events are wrapped in RAW format."""
        adapter = AGUIOutputAdapter()
        original = {"some": "data"}  # No type field

        result = adapter.passthrough(original)

        assert result == {"type": "RAW", "event": {"some": "data"}}

    def test_passthrough_wraps_primitive(self) -> None:
        """Test that primitive values are wrapped."""
        adapter = AGUIOutputAdapter()
        original = "just a string"

        result = adapter.passthrough(original)

        assert result == {"type": "RAW", "event": "just a string"}


class TestAGUIOutputAdapterMessageId:
    """Tests for message ID management."""

    def test_ensure_message_id_generates_uuid(self) -> None:
        """Test that _ensure_message_id generates a UUID."""
        adapter = AGUIOutputAdapter()

        message_id = adapter._ensure_message_id()

        assert message_id is not None
        assert isinstance(message_id, str)
        assert len(message_id) > 0

    def test_ensure_message_id_reuses_existing(self) -> None:
        """Test that _ensure_message_id reuses existing ID."""
        adapter = AGUIOutputAdapter()

        first_id = adapter._ensure_message_id()
        second_id = adapter._ensure_message_id()

        assert first_id == second_id

    def test_reset_message_id(self) -> None:
        """Test that reset_message_id clears the ID."""
        adapter = AGUIOutputAdapter()

        # Generate an ID
        first_id = adapter._ensure_message_id()
        assert adapter._message_id is not None

        # Reset
        adapter.reset_message_id()
        assert adapter._message_id is None

        # New ID should be different
        second_id = adapter._ensure_message_id()
        assert second_id != first_id

    def test_text_events_use_same_message_id(self) -> None:
        """Test that consecutive text events use the same message ID."""
        adapter = AGUIOutputAdapter()

        event1 = TextDeltaEvent(delta="Hello ")
        event2 = TextDeltaEvent(delta="world!")

        result1 = adapter.to_protocol_event(event1)
        result2 = adapter.to_protocol_event(event2)

        assert result1 is not None
        assert result2 is not None
        assert result1["message_id"] == result2["message_id"]

    def test_reset_between_conversations(self) -> None:
        """Test resetting message ID between conversation turns."""
        adapter = AGUIOutputAdapter()

        # First turn
        event1 = TextDeltaEvent(delta="Turn 1")
        result1 = adapter.to_protocol_event(event1)
        first_message_id = result1["message_id"] if result1 else None

        # Reset for new turn
        adapter.reset_message_id()

        # Second turn
        event2 = TextDeltaEvent(delta="Turn 2")
        result2 = adapter.to_protocol_event(event2)
        second_message_id = result2["message_id"] if result2 else None

        assert first_message_id is not None
        assert second_message_id is not None
        assert first_message_id != second_message_id


class TestAGUIOutputAdapterIntegration:
    """Integration tests for AGUIOutputAdapter."""

    def test_full_block_lifecycle(self) -> None:
        """Test converting a full block lifecycle to AG-UI events."""
        adapter = AGUIOutputAdapter()

        events = [
            BlockStartEvent(block_id="b1", syntax="md", start_line=1),
            BlockHeaderDeltaEvent(
                block_id="b1",
                syntax="md",
                delta="```python",
                current_line=1,
                accumulated_size=10,
            ),
            BlockContentDeltaEvent(
                block_id="b1",
                syntax="md",
                delta="print('hello')",
                current_line=2,
                accumulated_size=25,
            ),
            BlockEndEvent(
                block_id="b1",
                block_type="code",
                syntax="md",
                start_line=1,
                end_line=3,
                metadata={"id": "b1", "block_type": "code"},
                content={"raw_content": "print('hello')"},
                raw_content="```python\nprint('hello')\n```",
                hash_id="xyz123",
            ),
        ]

        results = [adapter.to_protocol_event(e) for e in events]

        # All events should produce results with ALL filter
        assert all(r is not None for r in results)

        # Check event names
        assert results[0]["name"] == "streamblocks.block_start"
        assert results[1]["name"] == "streamblocks.block_delta"
        assert results[2]["name"] == "streamblocks.block_delta"
        assert results[3]["name"] == "streamblocks.block_end"

    def test_mixed_text_and_blocks(self) -> None:
        """Test handling mixed text and block events."""
        adapter = AGUIOutputAdapter()

        events: list[Any] = [
            TextDeltaEvent(delta="Before block"),
            BlockStartEvent(block_id="b1", syntax="md", start_line=1),
            BlockEndEvent(
                block_id="b1",
                block_type="code",
                syntax="md",
                start_line=1,
                end_line=2,
                metadata={},
                content={},
                raw_content="block",
                hash_id="h",
            ),
            TextDeltaEvent(delta="After block"),
        ]

        results = [adapter.to_protocol_event(e) for e in events]

        # Check types
        assert results[0]["type"] == "TEXT_MESSAGE_CONTENT"
        assert results[1]["type"] == "CUSTOM"
        assert results[2]["type"] == "CUSTOM"
        assert results[3]["type"] == "TEXT_MESSAGE_CONTENT"

        # Text events should have same message ID
        assert results[0]["message_id"] == results[3]["message_id"]
