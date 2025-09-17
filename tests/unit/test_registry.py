"""Tests for BlockRegistry."""

import pytest
from pydantic import BaseModel

from streamblocks.core import BlockCandidate, BlockRegistry
from streamblocks.core.types import DetectionResult, ParseResult

# Test constants
EXPECTED_SYNTAX_COUNT = 3
EXPECTED_TYPE_B_COUNT = 2
EXPECTED_TYPE_C_COUNT = 2


class MockSyntax:
    """Mock syntax for testing."""

    def __init__(self, name: str):
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def detect_line(self, line: str, context: BlockCandidate | None = None) -> DetectionResult:
        return DetectionResult()

    def should_accumulate_metadata(self, candidate: BlockCandidate) -> bool:
        return False

    def parse_block(self, candidate: BlockCandidate) -> ParseResult[BaseModel, BaseModel]:
        return ParseResult[BaseModel, BaseModel](success=False)

    def validate_block(self, metadata: object, content: object) -> bool:
        return True

    def get_opening_pattern(self) -> str | None:
        return None

    def get_closing_pattern(self) -> str | None:
        return None

    def supports_nested_blocks(self) -> bool:
        return False

    def get_block_type_hints(self) -> list[str]:
        return []


class TestBlockRegistry:
    """Tests for BlockRegistry."""

    def test_initialization(self):
        """Test registry initialization."""
        registry = BlockRegistry()

        # Use public methods to verify initial state
        assert registry.get_syntaxes() == []
        assert not registry.has_syntax("any_syntax")

    def test_register_syntax_basic(self):
        """Test basic syntax registration."""
        registry = BlockRegistry()
        syntax = MockSyntax("test_syntax")

        registry.register_syntax(syntax)

        # Use public methods to verify registration
        assert registry.has_syntax("test_syntax")
        found = registry.get_syntax_by_name("test_syntax")
        assert found is syntax

    def test_register_syntax_with_block_types(self):
        """Test registering syntax with block types."""
        registry = BlockRegistry()
        syntax = MockSyntax("test_syntax")

        registry.register_syntax(syntax, block_types=["type1", "type2"])

        # Use public methods to verify block type registration
        type1_syntaxes = registry.get_syntaxes_for_block_type("type1")
        type2_syntaxes = registry.get_syntaxes_for_block_type("type2")
        assert len(type1_syntaxes) == 1
        assert len(type2_syntaxes) == 1
        assert type1_syntaxes[0].name == "test_syntax"
        assert type2_syntaxes[0].name == "test_syntax"

    def test_register_duplicate_name_raises(self):
        """Test that registering duplicate name raises error."""
        registry = BlockRegistry()
        syntax1 = MockSyntax("test_syntax")
        syntax2 = MockSyntax("test_syntax")

        registry.register_syntax(syntax1)

        with pytest.raises(ValueError) as exc_info:
            registry.register_syntax(syntax2)

        assert "already registered" in str(exc_info.value)

    def test_get_syntaxes(self):
        """Test getting all syntaxes in order."""
        registry = BlockRegistry()

        syntax1 = MockSyntax("syntax1")
        syntax2 = MockSyntax("syntax2")
        syntax3 = MockSyntax("syntax3")

        # Register with default priority (should maintain order by name)
        registry.register_syntax(syntax2, priority=50)
        registry.register_syntax(syntax1, priority=50)
        registry.register_syntax(syntax3, priority=50)

        syntaxes = registry.get_syntaxes()

        assert len(syntaxes) == EXPECTED_SYNTAX_COUNT
        # With same priority, should be ordered by name
        assert syntaxes[0].name == "syntax1"
        assert syntaxes[1].name == "syntax2"
        assert syntaxes[2].name == "syntax3"

    def test_get_syntax_by_name(self):
        """Test getting specific syntax by name."""
        registry = BlockRegistry()
        syntax = MockSyntax("test_syntax")

        registry.register_syntax(syntax)

        # Found case
        found = registry.get_syntax_by_name("test_syntax")
        assert found is syntax

        # Not found case
        not_found = registry.get_syntax_by_name("unknown")
        assert not_found is None

    def test_get_syntaxes_for_block_type(self):
        """Test getting syntaxes by block type."""
        registry = BlockRegistry()

        syntax1 = MockSyntax("syntax1")
        syntax2 = MockSyntax("syntax2")
        syntax3 = MockSyntax("syntax3")

        registry.register_syntax(syntax1, block_types=["type_a", "type_b"])
        registry.register_syntax(syntax2, block_types=["type_b", "type_c"])
        registry.register_syntax(syntax3, block_types=["type_c"])

        # Test type_a: only syntax1
        type_a_syntaxes = registry.get_syntaxes_for_block_type("type_a")
        assert len(type_a_syntaxes) == 1
        assert type_a_syntaxes[0].name == "syntax1"

        # Test type_b: syntax1 and syntax2
        type_b_syntaxes = registry.get_syntaxes_for_block_type("type_b")
        assert len(type_b_syntaxes) == EXPECTED_TYPE_B_COUNT
        assert {s.name for s in type_b_syntaxes} == {"syntax1", "syntax2"}

        # Test type_c: syntax2 and syntax3
        type_c_syntaxes = registry.get_syntaxes_for_block_type("type_c")
        assert len(type_c_syntaxes) == EXPECTED_TYPE_C_COUNT
        assert {s.name for s in type_c_syntaxes} == {"syntax2", "syntax3"}

        # Test unknown type
        unknown_syntaxes = registry.get_syntaxes_for_block_type("unknown")
        assert unknown_syntaxes == []

    def test_priority_ordering(self):
        """Test priority ordering."""
        registry = BlockRegistry()

        # Register with different priorities (lower number = higher priority)
        syntax1 = MockSyntax("high_priority")
        syntax2 = MockSyntax("medium_priority")
        syntax3 = MockSyntax("low_priority")

        # Register in reverse priority order
        registry.register_syntax(syntax3, priority=90)
        registry.register_syntax(syntax2, priority=50)
        registry.register_syntax(syntax1, priority=10)

        # Should be sorted by priority
        syntaxes = registry.get_syntaxes()
        assert len(syntaxes) == EXPECTED_SYNTAX_COUNT
        assert syntaxes[0].name == "high_priority"  # priority 10
        assert syntaxes[1].name == "medium_priority"  # priority 50
        assert syntaxes[2].name == "low_priority"  # priority 90

    def test_empty_registry(self):
        """Test operations on empty registry."""
        registry = BlockRegistry()

        assert registry.get_syntaxes() == []
        assert registry.get_syntax_by_name("any") is None
        assert registry.get_syntaxes_for_block_type("any") == []

    def test_multiple_block_types(self):
        """Test syntax handling multiple block types."""
        registry = BlockRegistry()
        syntax = MockSyntax("multi_type_syntax")

        block_types = ["code", "config", "data", "script"]
        registry.register_syntax(syntax, block_types=block_types)

        # Syntax should be registered for all types
        for block_type in block_types:
            syntaxes = registry.get_syntaxes_for_block_type(block_type)
            assert len(syntaxes) == 1
            assert syntaxes[0].name == "multi_type_syntax"

    def test_placeholder_methods(self):
        """Test enhanced methods."""
        registry = BlockRegistry()
        syntax = MockSyntax("test")

        # Create test models
        class TestMeta(BaseModel):
            id: str = "test"

        class TestContent(BaseModel):
            data: str = "test"

        # Test validator methods
        registry.register_validator("test_type", lambda x, y: True)
        is_valid, errors = registry.validate_block("test_type", TestMeta(), TestContent())
        assert is_valid is True
        assert errors == []

        # Test unregister (should raise for nonexistent)
        registry.register_syntax(syntax)
        registry.unregister_syntax("test")
        assert not registry.has_syntax("test")

        # Test unregister nonexistent raises
        with pytest.raises(KeyError):
            registry.unregister_syntax("nonexistent")

        # Test clear
        registry.register_syntax(MockSyntax("test2"))
        registry.clear()
        assert len(registry.get_syntaxes()) == 0
