"""Tests for BlockRegistry."""

import pytest

from streamblocks.core import BlockCandidate, BlockRegistry
from streamblocks.core.types import DetectionResult, ParseResult


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

    def parse_block(self, candidate: BlockCandidate) -> ParseResult:
        return ParseResult(success=False)


class TestBlockRegistry:
    """Tests for BlockRegistry."""

    def test_initialization(self):
        """Test registry initialization."""
        registry = BlockRegistry()

        assert registry._syntaxes == {}
        assert registry._block_types == {}
        assert registry._validators == {}
        assert registry._priority_order == []

    def test_register_syntax_basic(self):
        """Test basic syntax registration."""
        registry = BlockRegistry()
        syntax = MockSyntax("test_syntax")

        registry.register_syntax(syntax)

        assert "test_syntax" in registry._syntaxes
        assert registry._syntaxes["test_syntax"] is syntax
        assert "test_syntax" in registry._priority_order

    def test_register_syntax_with_block_types(self):
        """Test registering syntax with block types."""
        registry = BlockRegistry()
        syntax = MockSyntax("test_syntax")

        registry.register_syntax(syntax, block_types=["type1", "type2"])

        assert "type1" in registry._block_types
        assert "type2" in registry._block_types
        assert syntax in registry._block_types["type1"]
        assert syntax in registry._block_types["type2"]

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

        # Register in specific order
        registry.register_syntax(syntax2)
        registry.register_syntax(syntax1)
        registry.register_syntax(syntax3)

        syntaxes = registry.get_syntaxes()

        assert len(syntaxes) == 3
        # Order should match registration order (simplified version)
        assert syntaxes[0].name == "syntax2"
        assert syntaxes[1].name == "syntax1"
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
        assert len(type_b_syntaxes) == 2
        assert {s.name for s in type_b_syntaxes} == {"syntax1", "syntax2"}

        # Test type_c: syntax2 and syntax3
        type_c_syntaxes = registry.get_syntaxes_for_block_type("type_c")
        assert len(type_c_syntaxes) == 2
        assert {s.name for s in type_c_syntaxes} == {"syntax2", "syntax3"}

        # Test unknown type
        unknown_syntaxes = registry.get_syntaxes_for_block_type("unknown")
        assert unknown_syntaxes == []

    def test_priority_ordering(self):
        """Test priority ordering (simplified version)."""
        registry = BlockRegistry()

        # Register with different priorities (parameter is accepted but not used yet)
        syntax1 = MockSyntax("high_priority")
        syntax2 = MockSyntax("medium_priority")
        syntax3 = MockSyntax("low_priority")

        registry.register_syntax(syntax1, priority=10)
        registry.register_syntax(syntax2, priority=50)
        registry.register_syntax(syntax3, priority=90)

        # In this simplified version, order matches registration order
        syntaxes = registry.get_syntaxes()
        assert len(syntaxes) == 3

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
        """Test that placeholder methods exist and don't crash."""
        registry = BlockRegistry()

        # These should not raise errors
        registry.register_validator("test_type", lambda x, y: True)
        assert registry.validate_block("test_type", {}, {}) is True
        registry.unregister_syntax("nonexistent")
        registry.clear()
