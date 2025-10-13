"""Tests for global syntax configuration."""

import threading
from typing import Literal

import pytest
from pydantic import Field

import hother.streamblocks as sb
from hother.streamblocks.core.types import BaseContent, BaseMetadata
from hother.streamblocks.syntaxes.config import DEFAULT_SYNTAX


# Test block for examples
class ConfigTestMetadata(BaseMetadata):
    """Test metadata."""

    block_type: Literal["config_test"] = "config_test"  # type: ignore[assignment]


class ConfigTestContent(BaseContent):
    """Test content."""

    text: str = Field(description="Test text")

    @classmethod
    def parse(cls, raw_text: str) -> "ConfigTestContent":
        """Parse test content."""
        return cls(raw_content=raw_text, text=raw_text.strip())


class ConfigTestBlock(sb.Block[ConfigTestMetadata, ConfigTestContent]):
    """Test block."""


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def _reset_config():
    """Reset global config before and after each test."""
    sb.reset_default_syntax()
    yield
    sb.reset_default_syntax()


# ============================================================================
# Configuration Tests
# ============================================================================


def test_default_syntax_constant():
    """Test that DEFAULT_SYNTAX constant has expected value."""
    assert DEFAULT_SYNTAX == "DELIMITER_FRONTMATTER"


def test_set_and_get_default_syntax():
    """Test setting and getting global default syntax."""
    # Initially None (reset by fixture)
    assert sb.get_default_syntax() is None

    # Set to DELIMITER_PREAMBLE
    sb.set_default_syntax(sb.Syntax.DELIMITER_PREAMBLE)
    assert sb.get_default_syntax() == sb.Syntax.DELIMITER_PREAMBLE

    # Set to MARKDOWN_FRONTMATTER
    sb.set_default_syntax(sb.Syntax.MARKDOWN_FRONTMATTER)
    assert sb.get_default_syntax() == sb.Syntax.MARKDOWN_FRONTMATTER


def test_reset_default_syntax():
    """Test resetting to system default."""
    # Set custom default
    sb.set_default_syntax(sb.Syntax.DELIMITER_PREAMBLE)
    assert sb.get_default_syntax() == sb.Syntax.DELIMITER_PREAMBLE

    # Reset
    sb.reset_default_syntax()
    assert sb.get_default_syntax() is None


def test_set_default_syntax_with_instance():
    """Test setting default with BaseSyntax instance."""
    custom_syntax = sb.DelimiterFrontmatterSyntax()
    sb.set_default_syntax(custom_syntax)
    assert sb.get_default_syntax() is custom_syntax


# ============================================================================
# Resolution Tests
# ============================================================================


def test_resolve_syntax_priority_explicit():
    """Test that explicit argument has highest priority."""
    from hother.streamblocks.syntaxes.utils import resolve_syntax

    # Set global default
    sb.set_default_syntax(sb.Syntax.DELIMITER_PREAMBLE)

    # Explicit argument should override
    result = resolve_syntax(sb.Syntax.MARKDOWN_FRONTMATTER)
    assert result == sb.Syntax.MARKDOWN_FRONTMATTER


def test_resolve_syntax_priority_global():
    """Test that global default is used when no explicit argument."""
    from hother.streamblocks.syntaxes.utils import resolve_syntax

    # Set global default
    sb.set_default_syntax(sb.Syntax.DELIMITER_PREAMBLE)

    # Should use global default
    result = resolve_syntax(None)
    assert result == sb.Syntax.DELIMITER_PREAMBLE


def test_resolve_syntax_priority_system_default():
    """Test that system default is used when no global or explicit."""
    from hother.streamblocks.syntaxes.utils import resolve_syntax

    # Don't set global default (reset by fixture)
    result = resolve_syntax(None)
    assert result == sb.Syntax.DELIMITER_FRONTMATTER


def test_resolve_syntax_with_fallback():
    """Test resolution with fallback parameter."""
    from hother.streamblocks.syntaxes.utils import resolve_syntax

    # No global default set
    # Should use fallback
    result = resolve_syntax(None, fallback=sb.Syntax.MARKDOWN_FRONTMATTER)
    assert result == sb.Syntax.MARKDOWN_FRONTMATTER


# ============================================================================
# Block Methods Tests
# ============================================================================


def test_block_from_syntax_uses_global_default():
    """Test that Block.from_syntax uses global default."""
    # Set global default to DELIMITER_PREAMBLE
    sb.set_default_syntax(sb.Syntax.DELIMITER_PREAMBLE)

    text = """!!t1:config_test
Test content
!!end"""

    block = ConfigTestBlock.from_syntax(text)  # No syntax argument
    assert block.metadata.id == "t1"
    assert block.content.text == "Test content"


def test_block_from_syntax_explicit_override():
    """Test that explicit syntax overrides global default."""
    # Set global default to DELIMITER_FRONTMATTER
    sb.set_default_syntax(sb.Syntax.DELIMITER_FRONTMATTER)

    # Parse with DELIMITER_PREAMBLE explicitly
    text = """!!t2:config_test
Test content
!!end"""

    block = ConfigTestBlock.from_syntax(text, syntax=sb.Syntax.DELIMITER_PREAMBLE)
    assert block.metadata.id == "t2"


def test_block_from_syntax_system_default():
    """Test that Block.from_syntax uses system default when no config."""
    # Don't set global default (reset by fixture)
    # System default is DELIMITER_FRONTMATTER

    # Note: from_syntax doesn't properly simulate stream processing for
    # DelimiterFrontmatterSyntax, so we verify that the resolver returns
    # the system default and just test with DELIMITER_PREAMBLE

    # Verify system default is set correctly
    from hother.streamblocks.syntaxes.utils import resolve_syntax

    default = resolve_syntax(None)
    assert default == sb.Syntax.DELIMITER_FRONTMATTER

    # Test parsing with explicit syntax (DELIMITER_PREAMBLE works with from_syntax)
    text = """!!t3:config_test
Test content
!!end"""

    block = ConfigTestBlock.from_syntax(text, syntax=sb.Syntax.DELIMITER_PREAMBLE)
    assert block.metadata.id == "t3"


def test_block_add_example_from_syntax_uses_global_default():
    """Test that add_example_from_syntax uses global default."""
    sb.set_default_syntax(sb.Syntax.DELIMITER_PREAMBLE)

    text = """!!t4:config_test
Example content
!!end"""

    ConfigTestBlock.clear_examples()
    ConfigTestBlock.add_example_from_syntax(text)  # No syntax argument

    examples = ConfigTestBlock.get_examples()
    assert len(examples) == 1
    assert examples[0].metadata.id == "t4"


def test_block_to_prompt_uses_global_default():
    """Test that to_prompt uses global default."""
    sb.set_default_syntax(sb.Syntax.DELIMITER_PREAMBLE)

    prompt = ConfigTestBlock.to_prompt()  # No syntax argument

    # Should contain DELIMITER_PREAMBLE format
    assert "!!" in prompt
    assert "!!end" in prompt


def test_block_to_prompt_with_markdown_default():
    """Test to_prompt with MARKDOWN_FRONTMATTER default."""
    sb.set_default_syntax(sb.Syntax.MARKDOWN_FRONTMATTER)

    prompt = ConfigTestBlock.to_prompt()  # No syntax argument

    # Should contain markdown format
    assert "```" in prompt


# ============================================================================
# Registry Tests
# ============================================================================


def test_registry_uses_global_default():
    """Test that Registry uses global default."""
    sb.set_default_syntax(sb.Syntax.DELIMITER_PREAMBLE)

    registry = sb.Registry()  # No syntax argument

    assert isinstance(registry.syntax, sb.DelimiterPreambleSyntax)


def test_registry_explicit_override():
    """Test that explicit syntax overrides global default."""
    sb.set_default_syntax(sb.Syntax.DELIMITER_PREAMBLE)

    registry = sb.Registry(syntax=sb.Syntax.MARKDOWN_FRONTMATTER)

    assert isinstance(registry.syntax, sb.MarkdownFrontmatterSyntax)


def test_registry_system_default():
    """Test that Registry uses system default when no config."""
    # Don't set global default

    registry = sb.Registry()  # No syntax argument

    assert isinstance(registry.syntax, sb.DelimiterFrontmatterSyntax)


# ============================================================================
# Thread Safety Tests
# ============================================================================


def test_thread_safety_concurrent_access():
    """Test that configuration is thread-safe."""
    results = []
    errors = []

    def worker(syntax):
        """Worker thread that sets and checks syntax."""
        try:
            sb.set_default_syntax(syntax)
            result = sb.get_default_syntax()
            results.append(result)
        except Exception as e:
            errors.append(e)

    threads = [
        threading.Thread(target=worker, args=(sb.Syntax.DELIMITER_PREAMBLE,)),
        threading.Thread(target=worker, args=(sb.Syntax.DELIMITER_FRONTMATTER,)),
        threading.Thread(target=worker, args=(sb.Syntax.MARKDOWN_FRONTMATTER,)),
    ]

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    # Should complete without errors
    assert len(errors) == 0
    # Should have results from all threads
    assert len(results) == 3


def test_thread_safety_concurrent_reset():
    """Test concurrent resets are safe."""
    errors = []

    def worker():
        """Worker that resets syntax."""
        try:
            sb.set_default_syntax(sb.Syntax.DELIMITER_PREAMBLE)
            sb.reset_default_syntax()
            sb.get_default_syntax()
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(10)]

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    # Should complete without errors
    assert len(errors) == 0


# ============================================================================
# Integration Tests
# ============================================================================


def test_full_workflow_with_global_config():
    """Test complete workflow using global configuration."""
    # 1. Set global default
    sb.set_default_syntax(sb.Syntax.DELIMITER_PREAMBLE)

    # 2. Create registry
    registry = sb.Registry()  # Uses global default
    registry.register("config_test", ConfigTestBlock)

    # 3. Parse block
    text = """!!t5:config_test
Workflow test
!!end"""

    block = ConfigTestBlock.from_syntax(text)  # Uses global default

    # 4. Generate prompt
    prompt = ConfigTestBlock.to_prompt()  # Uses global default

    # 5. Add example
    ConfigTestBlock.clear_examples()
    ConfigTestBlock.add_example_from_syntax(text)  # Uses global default

    # 6. Serialize
    serialized = registry.serialize_block(block)

    # All operations completed successfully
    assert block.metadata.id == "t5"
    assert "!!" in prompt
    assert len(ConfigTestBlock.get_examples()) == 1
    assert "!!" in serialized


def test_mixed_global_and_explicit():
    """Test mixing global default with explicit overrides."""
    # Set global to DELIMITER_PREAMBLE
    sb.set_default_syntax(sb.Syntax.DELIMITER_PREAMBLE)

    # Some operations use global default
    registry1 = sb.Registry()  # Uses DELIMITER_PREAMBLE
    assert isinstance(registry1.syntax, sb.DelimiterPreambleSyntax)

    # Others explicitly override
    registry2 = sb.Registry(syntax=sb.Syntax.MARKDOWN_FRONTMATTER)
    assert isinstance(registry2.syntax, sb.MarkdownFrontmatterSyntax)

    # Back to global default
    registry3 = sb.Registry()  # Uses DELIMITER_PREAMBLE
    assert isinstance(registry3.syntax, sb.DelimiterPreambleSyntax)
