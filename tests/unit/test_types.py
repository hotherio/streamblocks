"""Tests for core type definitions."""

from pydantic import BaseModel

from streamblocks.core.types import (
    BlockState,
    DetectionResult,
    EventType,
    ParseResult,
    StreamEvent,
)


class TestEventType:
    """Tests for EventType enum."""

    def test_event_type_values(self):
        """Test that all event types have correct values."""
        assert EventType.RAW_TEXT.value == "raw_text"
        assert EventType.BLOCK_DELTA.value == "block_delta"
        assert EventType.BLOCK_EXTRACTED.value == "block_extracted"
        assert EventType.BLOCK_REJECTED.value == "block_rejected"

    def test_event_type_is_str_enum(self):
        """Test that EventType inherits from StrEnum."""
        assert isinstance(EventType.RAW_TEXT, str)
        assert EventType.RAW_TEXT.upper() == "RAW_TEXT"


class TestBlockState:
    """Tests for BlockState enum."""

    def test_block_state_values(self):
        """Test that all block states have correct values."""
        assert BlockState.SEARCHING.value == "searching"
        assert BlockState.HEADER_DETECTED.value == "header_detected"
        assert BlockState.ACCUMULATING_METADATA.value == "accumulating_metadata"
        assert BlockState.ACCUMULATING_CONTENT.value == "accumulating_content"
        assert BlockState.CLOSING_DETECTED.value == "closing_detected"
        assert BlockState.REJECTED.value == "rejected"
        assert BlockState.COMPLETED.value == "completed"

    def test_block_state_is_str_enum(self):
        """Test that BlockState inherits from StrEnum."""
        assert isinstance(BlockState.SEARCHING, str)


class TestStreamEvent:
    """Tests for StreamEvent model."""

    def test_stream_event_creation(self):
        """Test creating a basic stream event."""
        event: StreamEvent[BaseModel, BaseModel] = StreamEvent(type=EventType.RAW_TEXT, data="Hello, world!")
        assert event.type == EventType.RAW_TEXT
        assert event.data == "Hello, world!"
        assert event.metadata is None

    def test_stream_event_with_metadata(self):
        """Test creating stream event with metadata."""
        metadata = {"line_number": 42, "syntax": "test"}
        event: StreamEvent[BaseModel, BaseModel] = StreamEvent(
            type=EventType.BLOCK_DELTA, data="Block content", metadata=metadata
        )
        assert event.metadata == metadata

    def test_stream_event_serialization(self):
        """Test that stream events can be serialized."""
        event: StreamEvent[BaseModel, BaseModel] = StreamEvent(
            type=EventType.BLOCK_EXTRACTED, data="Test data", metadata={"key": "value"}
        )
        json_data = event.model_dump_json()
        assert isinstance(json_data, str)

        # Can reconstruct from JSON
        reconstructed = StreamEvent[BaseModel, BaseModel].model_validate_json(json_data)
        assert reconstructed.type == event.type
        assert reconstructed.data == event.data
        assert reconstructed.metadata == event.metadata

    def test_stream_event_generic_typing(self):
        """Test that StreamEvent works with generic types."""

        # Define test models
        class TestMetadata(BaseModel):
            id: str

        class TestContent(BaseModel):
            body: str

        # StreamEvent can be parameterized with these types
        event: StreamEvent[TestMetadata, TestContent] = StreamEvent(type=EventType.RAW_TEXT, data="test")
        assert event.data == "test"


class TestDetectionResult:
    """Tests for DetectionResult dataclass."""

    def test_detection_result_defaults(self):
        """Test DetectionResult default values."""
        result = DetectionResult()
        assert result.is_opening is False
        assert result.is_closing is False
        assert result.is_metadata_boundary is False
        assert result.metadata is None

    def test_detection_result_opening(self):
        """Test creating opening detection."""
        result = DetectionResult(is_opening=True)
        assert result.is_opening is True
        assert result.is_closing is False

    def test_detection_result_with_metadata(self):
        """Test detection with inline metadata."""
        metadata = {"id": "block123", "type": "test"}
        result = DetectionResult(is_opening=True, metadata=metadata)
        assert result.is_opening is True
        assert result.metadata == metadata

    def test_detection_result_combinations(self):
        """Test various detection combinations."""
        # Closing detection
        result = DetectionResult(is_closing=True)
        assert result.is_closing is True

        # Metadata boundary
        result = DetectionResult(is_metadata_boundary=True)
        assert result.is_metadata_boundary is True


class TestParseResult:
    """Tests for ParseResult dataclass."""

    def test_parse_result_success(self):
        """Test successful parse result."""

        class TestMetadata(BaseModel):
            id: str

        class TestContent(BaseModel):
            body: str

        metadata = TestMetadata(id="123")
        content = TestContent(body="Hello")

        result = ParseResult(success=True, metadata=metadata, content=content)
        assert result.success is True
        assert result.metadata == metadata
        assert result.content == content
        assert result.error is None

    def test_parse_result_failure(self):
        """Test failed parse result."""
        result: ParseResult[BaseModel, BaseModel] = ParseResult(success=False, error="Invalid YAML format")
        assert result.success is False
        assert result.metadata is None
        assert result.content is None
        assert result.error == "Invalid YAML format"

    def test_parse_result_generic_typing(self):
        """Test ParseResult with generic types."""

        class TestMetadata(BaseModel):
            version: int

        class TestContent(BaseModel):
            lines: list[str]

        # Type-safe result
        result: ParseResult[TestMetadata, TestContent] = ParseResult(
            success=True, metadata=TestMetadata(version=1), content=TestContent(lines=["a", "b"])
        )
        assert result.metadata is not None
        assert result.content is not None
        assert result.metadata.version == 1
        assert result.content.lines == ["a", "b"]
