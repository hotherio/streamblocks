"""Tests for AG-UI input adapter."""

from __future__ import annotations

# Import actual AG-UI types for proper isinstance checks
from ag_ui.core import (
    EventType,
    RunFinishedEvent,
    RunStartedEvent,
    TextMessageChunkEvent,
    TextMessageContentEvent,
    ToolCallEndEvent,
    ToolCallStartEvent,
)

from hother.streamblocks.adapters.categories import EventCategory
from hother.streamblocks.extensions.agui.input_adapter import AGUIInputAdapter


def create_text_message_content_event(delta: str = "test", message_id: str = "msg-1") -> TextMessageContentEvent:
    """Create a TextMessageContentEvent for testing."""
    return TextMessageContentEvent(
        type=EventType.TEXT_MESSAGE_CONTENT,
        delta=delta,
        message_id=message_id,
    )


def create_text_message_chunk_event(delta: str = "test", message_id: str = "msg-1") -> TextMessageChunkEvent:
    """Create a TextMessageChunkEvent for testing."""
    return TextMessageChunkEvent(
        type=EventType.TEXT_MESSAGE_CHUNK,
        delta=delta,
        message_id=message_id,
    )


def create_run_finished_event(thread_id: str = "thread-1", run_id: str = "run-1") -> RunFinishedEvent:
    """Create a RunFinishedEvent for testing."""
    return RunFinishedEvent(
        type=EventType.RUN_FINISHED,
        thread_id=thread_id,
        run_id=run_id,
    )


def create_run_started_event(thread_id: str = "thread-1", run_id: str = "run-1") -> RunStartedEvent:
    """Create a RunStartedEvent for testing."""
    return RunStartedEvent(
        type=EventType.RUN_STARTED,
        thread_id=thread_id,
        run_id=run_id,
    )


def create_tool_call_start_event(tool_call_id: str = "tool-1", tool_call_name: str = "test_tool") -> ToolCallStartEvent:
    """Create a ToolCallStartEvent for testing."""
    return ToolCallStartEvent(
        type=EventType.TOOL_CALL_START,
        tool_call_id=tool_call_id,
        tool_call_name=tool_call_name,
    )


def create_tool_call_end_event(tool_call_id: str = "tool-1") -> ToolCallEndEvent:
    """Create a ToolCallEndEvent for testing."""
    return ToolCallEndEvent(
        type=EventType.TOOL_CALL_END,
        tool_call_id=tool_call_id,
    )


class TestAGUIInputAdapterCategorize:
    """Tests for AGUIInputAdapter.categorize()."""

    def test_categorize_text_message_content(self) -> None:
        """Test categorizing TEXT_MESSAGE_CONTENT event."""
        adapter = AGUIInputAdapter()
        event = create_text_message_content_event(delta="Hello")

        result = adapter.categorize(event)

        assert result == EventCategory.TEXT_CONTENT

    def test_categorize_text_message_chunk(self) -> None:
        """Test categorizing TEXT_MESSAGE_CHUNK event."""
        adapter = AGUIInputAdapter()
        event = create_text_message_chunk_event(delta="Hello")

        result = adapter.categorize(event)

        assert result == EventCategory.TEXT_CONTENT

    def test_categorize_run_finished_as_passthrough(self) -> None:
        """Test that RUN_FINISHED is categorized as PASSTHROUGH."""
        adapter = AGUIInputAdapter()
        event = create_run_finished_event()

        result = adapter.categorize(event)

        assert result == EventCategory.PASSTHROUGH

    def test_categorize_run_started_as_passthrough(self) -> None:
        """Test that RUN_STARTED is categorized as PASSTHROUGH."""
        adapter = AGUIInputAdapter()
        event = create_run_started_event()

        result = adapter.categorize(event)

        assert result == EventCategory.PASSTHROUGH

    def test_categorize_tool_call_as_passthrough(self) -> None:
        """Test that tool call events are categorized as PASSTHROUGH."""
        adapter = AGUIInputAdapter()
        event = create_tool_call_start_event()

        result = adapter.categorize(event)

        assert result == EventCategory.PASSTHROUGH


class TestAGUIInputAdapterExtractText:
    """Tests for AGUIInputAdapter.extract_text()."""

    def test_extract_text_from_text_message_content(self) -> None:
        """Test extracting delta text from TEXT_MESSAGE_CONTENT event."""
        adapter = AGUIInputAdapter()
        event = create_text_message_content_event(delta="Hello, world!")

        result = adapter.extract_text(event)

        assert result == "Hello, world!"

    def test_extract_text_from_text_message_chunk(self) -> None:
        """Test extracting delta from TEXT_MESSAGE_CHUNK event."""
        adapter = AGUIInputAdapter()
        event = create_text_message_chunk_event(delta="Chunk content")

        result = adapter.extract_text(event)

        assert result == "Chunk content"

    def test_extract_text_from_non_text_event(self) -> None:
        """Test extracting text from non-text event returns None."""
        adapter = AGUIInputAdapter()
        event = create_run_started_event()

        result = adapter.extract_text(event)

        assert result is None

    def test_extract_text_from_run_finished(self) -> None:
        """Test extracting text from RUN_FINISHED event returns None."""
        adapter = AGUIInputAdapter()
        event = create_run_finished_event()

        result = adapter.extract_text(event)

        assert result is None


class TestAGUIInputAdapterIsComplete:
    """Tests for AGUIInputAdapter.is_complete()."""

    def test_is_complete_run_finished(self) -> None:
        """Test that RUN_FINISHED event returns True."""
        adapter = AGUIInputAdapter()
        event = create_run_finished_event()

        result = adapter.is_complete(event)

        assert result is True

    def test_is_complete_text_content_event(self) -> None:
        """Test that text content events return False."""
        adapter = AGUIInputAdapter()
        event = create_text_message_content_event()

        result = adapter.is_complete(event)

        assert result is False

    def test_is_complete_run_started(self) -> None:
        """Test that RUN_STARTED returns False."""
        adapter = AGUIInputAdapter()
        event = create_run_started_event()

        result = adapter.is_complete(event)

        assert result is False

    def test_is_complete_tool_call(self) -> None:
        """Test that tool call events return False."""
        adapter = AGUIInputAdapter()
        event = create_tool_call_start_event()

        result = adapter.is_complete(event)

        assert result is False


class TestAGUIInputAdapterGetMetadata:
    """Tests for AGUIInputAdapter.get_metadata()."""

    def test_get_metadata_with_text_content_event(self) -> None:
        """Test getting metadata from text content event."""
        adapter = AGUIInputAdapter()
        event = create_text_message_content_event()

        result = adapter.get_metadata(event)

        assert result is not None
        assert result["event_type"] == "TEXT_MESSAGE_CONTENT"

    def test_get_metadata_with_run_finished(self) -> None:
        """Test getting metadata from RUN_FINISHED event."""
        adapter = AGUIInputAdapter()
        event = create_run_finished_event()

        result = adapter.get_metadata(event)

        assert result is not None
        assert result["event_type"] == "RUN_FINISHED"

    def test_get_metadata_with_timestamp(self) -> None:
        """Test getting metadata with timestamp."""
        adapter = AGUIInputAdapter()
        event = TextMessageContentEvent(
            type=EventType.TEXT_MESSAGE_CONTENT,
            delta="Hello",
            message_id="msg-1",
            timestamp=1234567890,
        )

        result = adapter.get_metadata(event)

        assert result is not None
        assert result["event_type"] == "TEXT_MESSAGE_CONTENT"
        assert result["timestamp"] == 1234567890


class TestAGUIInputAdapterIntegration:
    """Integration tests for AGUIInputAdapter."""

    def test_full_event_processing_flow(self) -> None:
        """Test processing a sequence of events."""
        adapter = AGUIInputAdapter()

        # Simulate event sequence
        events = [
            create_run_started_event(),
            create_text_message_content_event(delta="Hello "),
            create_text_message_content_event(delta="world!"),
            create_run_finished_event(),
        ]

        extracted_text: list[str] = []
        for event in events:
            category = adapter.categorize(event)
            if category == EventCategory.TEXT_CONTENT:
                text = adapter.extract_text(event)
                if text:
                    extracted_text.append(text)

            if adapter.is_complete(event):
                break

        assert extracted_text == ["Hello ", "world!"]

    def test_mixed_event_stream(self) -> None:
        """Test handling a mixed stream of events."""
        adapter = AGUIInputAdapter()

        events = [
            create_run_started_event(),
            create_tool_call_start_event(),
            create_text_message_chunk_event(delta="Result"),
            create_run_finished_event(),
        ]

        results: list[dict[str, object]] = []
        for event in events:
            category = adapter.categorize(event)
            metadata = adapter.get_metadata(event)
            text = adapter.extract_text(event) if category == EventCategory.TEXT_CONTENT else None

            results.append(
                {
                    "category": category,
                    "text": text,
                    "metadata": metadata,
                    "complete": adapter.is_complete(event),
                }
            )

        # First event: RUN_STARTED - passthrough
        assert results[0]["category"] == EventCategory.PASSTHROUGH
        assert results[0]["text"] is None
        assert results[0]["complete"] is False

        # Second event: TOOL_CALL_START - passthrough
        assert results[1]["category"] == EventCategory.PASSTHROUGH
        assert results[1]["text"] is None

        # Third event: TEXT_MESSAGE_CHUNK - text content
        assert results[2]["category"] == EventCategory.TEXT_CONTENT
        assert results[2]["text"] == "Result"

        # Fourth event: RUN_FINISHED - complete
        assert results[3]["category"] == EventCategory.PASSTHROUGH
        assert results[3]["complete"] is True


class TestAGUIInputAdapterNativeModulePrefix:
    """Tests for native_module_prefix class variable."""

    def test_native_module_prefix_defined(self) -> None:
        """Test that native_module_prefix is defined."""
        assert hasattr(AGUIInputAdapter, "native_module_prefix")
        assert AGUIInputAdapter.native_module_prefix == "ag_ui."

    def test_native_module_prefix_accessible_on_instance(self) -> None:
        """Test that native_module_prefix is accessible on instance."""
        adapter = AGUIInputAdapter()
        assert adapter.native_module_prefix == "ag_ui."
