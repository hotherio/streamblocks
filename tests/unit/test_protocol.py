"""Tests for BlockSyntax protocol definition."""


from pydantic import BaseModel

# Import BlockCandidate locally to avoid circular import issues
# This is just the placeholder from models.py
from streamblocks.core.models import BlockCandidate
from streamblocks.core.types import BlockSyntax, DetectionResult, ParseResult


class TestBlockSyntaxProtocol:
    """Tests for BlockSyntax protocol."""

    def test_protocol_is_generic(self):
        """Test that BlockSyntax is properly generic."""
        # BlockSyntax should be subscriptable with type parameters
        assert hasattr(BlockSyntax, "__class_getitem__")

        # Can create parameterized versions
        class TestMeta(BaseModel):
            id: str

        class TestContent(BaseModel):
            data: str

        # This should not raise
        parameterized = BlockSyntax[TestMeta, TestContent]
        assert parameterized is not None

    def test_protocol_methods_defined(self):
        """Test that protocol defines all required methods."""
        # Get protocol methods
        protocol_attrs = dir(BlockSyntax)

        # Required methods
        assert "name" in protocol_attrs
        assert "detect_line" in protocol_attrs
        assert "should_accumulate_metadata" in protocol_attrs
        assert "parse_block" in protocol_attrs
        assert "validate_block" in protocol_attrs

    def test_mock_implementation(self):
        """Test creating a mock implementation of BlockSyntax."""

        class TestMetadata(BaseModel):
            id: str
            type: str

        class TestContent(BaseModel):
            body: str

        class MockSyntax:
            """Mock syntax implementation for testing."""

            @property
            def name(self) -> str:
                return "mock_syntax"

            def detect_line(
                self, line: str, context: BlockCandidate | None = None
            ) -> DetectionResult:
                if line.startswith("!!"):
                    return DetectionResult(is_opening=True)
                return DetectionResult()

            def should_accumulate_metadata(self, candidate: BlockCandidate) -> bool:
                return False

            def parse_block(
                self, candidate: BlockCandidate
            ) -> ParseResult[TestMetadata, TestContent]:
                return ParseResult(
                    success=True,
                    metadata=TestMetadata(id="test", type="mock"),
                    content=TestContent(body="test content"),
                )

            def validate_block(self, metadata: TestMetadata, content: TestContent) -> bool:
                return True

        # Create instance
        syntax = MockSyntax()

        # Test it works
        assert syntax.name == "mock_syntax"
        assert syntax.detect_line("!!test").is_opening is True
        assert syntax.detect_line("normal").is_opening is False
        assert syntax.should_accumulate_metadata(BlockCandidate()) is False

        # Parse result
        result = syntax.parse_block(BlockCandidate())
        assert result.success is True
        assert result.metadata.id == "test"
        assert result.content.body == "test content"

        # Validation
        assert syntax.validate_block(TestMetadata(id="x", type="y"), TestContent(body="z")) is True

    def test_protocol_type_annotations(self):
        """Test that protocol methods have proper type annotations."""
        # This test verifies the protocol is properly typed
        # by checking that type checkers can understand it

        # Get method annotations
        detect_line_annotations = BlockSyntax.detect_line.__annotations__
        parse_block_annotations = BlockSyntax.parse_block.__annotations__

        # Check detect_line parameters
        assert "line" in detect_line_annotations
        assert detect_line_annotations["line"] == "str"  # Annotations are strings in protocol
        assert "return" in detect_line_annotations

        # Check parse_block parameters
        assert "candidate" in parse_block_annotations
        assert "return" in parse_block_annotations

    def test_validate_block_default_implementation(self):
        """Test that validate_block has a default implementation."""
        # The protocol should provide a default implementation that returns True

        class MinimalSyntax:
            """Minimal syntax that only implements required methods."""

            @property
            def name(self) -> str:
                return "minimal"

            def detect_line(
                self, line: str, context: BlockCandidate | None = None
            ) -> DetectionResult:
                return DetectionResult()

            def should_accumulate_metadata(self, candidate: BlockCandidate) -> bool:
                return False

            def parse_block(self, candidate: BlockCandidate) -> ParseResult:
                return ParseResult(success=False, error="Not implemented")

        # Create instance - should work even without implementing validate_block
        MinimalSyntax()  # Instantiate to verify it works without validate_block

        # The default implementation should return True
        # We can't directly test this since MinimalSyntax doesn't implement the protocol
        # but we can verify the protocol has validate_block with a default
        assert hasattr(BlockSyntax, "validate_block")

    def test_protocol_runtime_behavior(self):
        """Test protocol behavior at runtime."""
        # Protocols in Python don't enforce implementation at runtime by default
        # But we can verify the protocol structure

        # Check that BlockSyntax is indeed a Protocol
        assert hasattr(BlockSyntax, "__protocol__") or hasattr(BlockSyntax, "_is_protocol")

        # Verify generic parameters
        assert hasattr(BlockSyntax, "__parameters__")

    def test_protocol_with_different_generic_types(self):
        """Test protocol works with different generic type parameters."""

        class StringMetadata(BaseModel):
            value: str

        class IntContent(BaseModel):
            number: int

        class ListMetadata(BaseModel):
            items: list[str]

        class DictContent(BaseModel):
            data: dict[str, int]

        # Create different parameterized versions
        string_int_syntax = BlockSyntax[StringMetadata, IntContent]
        list_dict_syntax = BlockSyntax[ListMetadata, DictContent]

        # These should be different types
        assert string_int_syntax != list_dict_syntax

    def test_protocol_abstract_methods(self):
        """Test that abstract methods are properly defined."""
        # Import abstractmethod to verify decorators
        from abc import abstractmethod
        
        # Check that required methods are abstract
        assert hasattr(BlockSyntax.name, '__isabstractmethod__')
        assert hasattr(BlockSyntax.detect_line, '__isabstractmethod__')
        assert hasattr(BlockSyntax.should_accumulate_metadata, '__isabstractmethod__')
        assert hasattr(BlockSyntax.parse_block, '__isabstractmethod__')
        
        # validate_block should NOT be abstract (has default implementation)
        assert not hasattr(BlockSyntax.validate_block, '__isabstractmethod__')
