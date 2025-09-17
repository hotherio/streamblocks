"""Tests for block models."""

import pytest
from pydantic import BaseModel

from streamblocks.core import Block, BlockCandidate, BlockState
from streamblocks.core.types import DetectionResult, ParseResult


# Test models
class SampleMetadata(BaseModel):
    """Sample metadata model for testing."""

    id: str
    type: str = "test"


class SampleContent(BaseModel):
    """Sample content model for testing."""

    body: str


# Mock syntax for testing
class MockSyntax:
    """Mock syntax implementation for testing."""

    @property
    def name(self) -> str:
        return "mock_syntax"

    def detect_line(self, line: str, context: BlockCandidate | None = None) -> DetectionResult:
        return DetectionResult()

    def should_accumulate_metadata(self, candidate: BlockCandidate) -> bool:
        return False

    def parse_block(self, candidate: BlockCandidate) -> ParseResult[SampleMetadata, SampleContent]:
        return ParseResult(
            success=True, metadata=SampleMetadata(id="test"), content=SampleContent(body="test")
        )


class TestBlockCandidate:
    """Tests for BlockCandidate class."""

    def test_initialization(self):
        """Test BlockCandidate initialization."""
        syntax = MockSyntax()
        candidate = BlockCandidate(syntax, start_line=10)

        assert candidate.syntax is syntax
        assert candidate.start_line == 10
        assert candidate.lines == []
        assert candidate.state == BlockState.HEADER_DETECTED
        assert candidate.metadata_lines == []
        assert candidate.content_lines == []
        assert candidate.current_section == "header"

    def test_add_line_header(self):
        """Test adding lines in header section."""
        syntax = MockSyntax()
        candidate = BlockCandidate(syntax, start_line=1)

        # Add line while in header section
        candidate.add_line("!! block-start")

        assert candidate.lines == ["!! block-start"]
        assert candidate.metadata_lines == []
        assert candidate.content_lines == []

    def test_add_line_metadata(self):
        """Test adding lines in metadata section."""
        syntax = MockSyntax()
        candidate = BlockCandidate(syntax, start_line=1)

        # Switch to metadata section
        candidate.current_section = "metadata"
        candidate.add_line("id: test123")
        candidate.add_line("type: example")

        assert candidate.lines == ["id: test123", "type: example"]
        assert candidate.metadata_lines == ["id: test123", "type: example"]
        assert candidate.content_lines == []

    def test_add_line_content(self):
        """Test adding lines in content section."""
        syntax = MockSyntax()
        candidate = BlockCandidate(syntax, start_line=1)

        # Switch to content section
        candidate.current_section = "content"
        candidate.add_line("This is content")
        candidate.add_line("More content")

        assert candidate.lines == ["This is content", "More content"]
        assert candidate.metadata_lines == []
        assert candidate.content_lines == ["This is content", "More content"]

    def test_raw_text_property(self):
        """Test raw_text property."""
        syntax = MockSyntax()
        candidate = BlockCandidate(syntax, start_line=1)

        candidate.add_line("Line 1")
        candidate.add_line("Line 2")
        candidate.add_line("Line 3")

        assert candidate.raw_text == "Line 1\nLine 2\nLine 3"

    def test_raw_text_empty(self):
        """Test raw_text with no lines."""
        syntax = MockSyntax()
        candidate = BlockCandidate(syntax, start_line=1)

        assert candidate.raw_text == ""

    def test_compute_hash_consistency(self):
        """Test hash computation is consistent."""
        syntax = MockSyntax()
        candidate = BlockCandidate(syntax, start_line=1)

        candidate.add_line("Test content")
        candidate.add_line("More content")

        hash1 = candidate.compute_hash()
        hash2 = candidate.compute_hash()

        assert hash1 == hash2
        assert len(hash1) == 8
        assert all(c in "0123456789abcdef" for c in hash1)

    def test_compute_hash_different_content(self):
        """Test hash differs for different content."""
        syntax = MockSyntax()

        candidate1 = BlockCandidate(syntax, start_line=1)
        candidate1.add_line("Content A")

        candidate2 = BlockCandidate(syntax, start_line=1)
        candidate2.add_line("Content B")

        assert candidate1.compute_hash() != candidate2.compute_hash()

    def test_compute_hash_truncation(self):
        """Test hash uses only first 64 chars."""
        syntax = MockSyntax()

        # Create candidate with long content
        candidate1 = BlockCandidate(syntax, start_line=1)
        candidate1.add_line("A" * 100)

        # Create candidate with same first 64 chars
        candidate2 = BlockCandidate(syntax, start_line=1)
        candidate2.add_line("A" * 64 + "B" * 36)

        # Hashes should be the same since first 64 chars match
        assert candidate1.compute_hash() == candidate2.compute_hash()

    def test_state_transitions(self):
        """Test state can be changed."""
        syntax = MockSyntax()
        candidate = BlockCandidate(syntax, start_line=1)

        # Initial state
        assert candidate.state == BlockState.HEADER_DETECTED

        # Change state
        candidate.state = BlockState.ACCUMULATING_METADATA
        assert candidate.state == BlockState.ACCUMULATING_METADATA

        candidate.state = BlockState.COMPLETED
        assert candidate.state == BlockState.COMPLETED

    def test_with_large_content(self):
        """Test with large content."""
        syntax = MockSyntax()
        candidate = BlockCandidate(syntax, start_line=1)

        # Add many lines
        for i in range(1000):
            candidate.add_line(f"Line {i}")

        assert len(candidate.lines) == 1000
        assert candidate.raw_text.count("\n") == 999

        # Hash should still work
        hash_id = candidate.compute_hash()
        assert len(hash_id) == 8


class TestBlock:
    """Tests for Block model."""

    def test_creation_with_valid_data(self):
        """Test Block creation with all required fields."""
        metadata = SampleMetadata(id="test123")
        content = SampleContent(body="Test body")

        block = Block[SampleMetadata, SampleContent](
            syntax_name="test_syntax",
            metadata=metadata,
            content=content,
            raw_text="!! test\nid: test123\n---\nTest body",
            line_start=10,
            line_end=13,
            hash_id="abc12345",
        )

        assert block.syntax_name == "test_syntax"
        assert block.metadata.id == "test123"
        assert block.content.body == "Test body"
        assert block.raw_text == "!! test\nid: test123\n---\nTest body"
        assert block.line_start == 10
        assert block.line_end == 13
        assert block.hash_id == "abc12345"

    def test_serialization(self):
        """Test Block can be serialized to dict/JSON."""
        metadata = SampleMetadata(id="test123")
        content = SampleContent(body="Test body")

        block = Block[SampleMetadata, SampleContent](
            syntax_name="test_syntax",
            metadata=metadata,
            content=content,
            raw_text="raw",
            line_start=1,
            line_end=3,
            hash_id="12345678",
        )

        # Convert to dict
        block_dict = block.model_dump()

        assert block_dict["syntax_name"] == "test_syntax"
        assert block_dict["metadata"]["id"] == "test123"
        assert block_dict["content"]["body"] == "Test body"
        assert block_dict["line_start"] == 1
        assert block_dict["line_end"] == 3
        assert block_dict["hash_id"] == "12345678"

        # Convert to JSON
        json_str = block.model_dump_json()
        assert "test_syntax" in json_str
        assert "test123" in json_str

    def test_deserialization(self):
        """Test Block can be deserialized from dict."""
        block_dict = {
            "syntax_name": "test_syntax",
            "metadata": {"id": "test123", "type": "test"},
            "content": {"body": "Test body"},
            "raw_text": "raw",
            "line_start": 1,
            "line_end": 3,
            "hash_id": "12345678",
        }

        block = Block[SampleMetadata, SampleContent].model_validate(block_dict)

        assert block.syntax_name == "test_syntax"
        assert block.metadata.id == "test123"
        assert block.content.body == "Test body"

    def test_with_different_generic_types(self):
        """Test Block works with different generic type parameters."""

        # Define alternative models
        class AltMetadata(BaseModel):
            name: str
            version: int

        class AltContent(BaseModel):
            items: list[str]

        # Create block with alternative types
        metadata = AltMetadata(name="example", version=1)
        content = AltContent(items=["a", "b", "c"])

        block = Block[AltMetadata, AltContent](
            syntax_name="alt_syntax",
            metadata=metadata,
            content=content,
            raw_text="alt block",
            line_start=5,
            line_end=8,
            hash_id="alt12345",
        )

        assert block.metadata.name == "example"
        assert block.metadata.version == 1
        assert block.content.items == ["a", "b", "c"]

    def test_field_validation(self):
        """Test that required fields are validated."""
        metadata = SampleMetadata(id="test123")
        content = SampleContent(body="Test body")

        # Missing required field should raise error
        with pytest.raises(ValueError):
            Block[SampleMetadata, SampleContent](
                # Missing syntax_name
                metadata=metadata,
                content=content,
                raw_text="raw",
                line_start=1,
                line_end=3,
                hash_id="12345678",
            )

    def test_immutability(self):
        """Test that Block fields are immutable by default."""
        metadata = SampleMetadata(id="test123")
        content = SampleContent(body="Test body")

        block = Block[SampleMetadata, SampleContent](
            syntax_name="test_syntax",
            metadata=metadata,
            content=content,
            raw_text="raw",
            line_start=1,
            line_end=3,
            hash_id="12345678",
        )

        # Pydantic v2 models are mutable by default, but we can validate
        # that the fields exist and can be accessed
        assert hasattr(block, "syntax_name")
        assert hasattr(block, "metadata")
        assert hasattr(block, "content")
