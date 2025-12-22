"""Shared pytest fixtures for StreamBlocks tests."""

from collections.abc import AsyncIterator, Callable

import pytest

from hother.streamblocks import (
    DelimiterFrontmatterSyntax,
    DelimiterPreambleSyntax,
    Registry,
    StreamBlockProcessor,
)
from hother.streamblocks.blocks import FileOperations


@pytest.fixture
def delimiter_preamble_syntax() -> DelimiterPreambleSyntax:
    """Create a DelimiterPreambleSyntax instance."""
    return DelimiterPreambleSyntax()


@pytest.fixture
def delimiter_frontmatter_syntax() -> DelimiterFrontmatterSyntax:
    """Create a DelimiterFrontmatterSyntax instance."""
    return DelimiterFrontmatterSyntax()


@pytest.fixture
def file_operations_registry(
    delimiter_preamble_syntax: DelimiterPreambleSyntax,
) -> Registry:
    """Create a Registry with FileOperations registered."""
    registry = Registry(syntax=delimiter_preamble_syntax)
    registry.register("files_operations", FileOperations)
    return registry


@pytest.fixture
def frontmatter_registry(
    delimiter_frontmatter_syntax: DelimiterFrontmatterSyntax,
) -> Registry:
    """Create a Registry with frontmatter syntax."""
    return Registry(syntax=delimiter_frontmatter_syntax)


@pytest.fixture
def processor(file_operations_registry: Registry) -> StreamBlockProcessor:
    """Create a StreamBlockProcessor with FileOperations."""
    return StreamBlockProcessor(file_operations_registry, emit_text_deltas=False)


@pytest.fixture
def frontmatter_processor(frontmatter_registry: Registry) -> StreamBlockProcessor:
    """Create a StreamBlockProcessor with frontmatter syntax."""
    return StreamBlockProcessor(frontmatter_registry, emit_text_deltas=False)


@pytest.fixture
def mock_stream() -> Callable[[str], AsyncIterator[str]]:
    """Factory fixture for creating mock async streams from text."""

    async def _create(text: str) -> AsyncIterator[str]:
        for line in text.split("\n"):
            yield line + "\n"

    return _create
