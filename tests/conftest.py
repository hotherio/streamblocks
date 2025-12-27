"""Shared pytest fixtures for StreamBlocks tests."""

import time
from collections.abc import AsyncIterator, Callable, Generator
from contextlib import contextmanager
from typing import Any

import pytest

from hother.streamblocks import (
    DelimiterFrontmatterSyntax,
    DelimiterPreambleSyntax,
    Registry,
    StreamBlockProcessor,
)
from hother.streamblocks.core.processor import ProcessorConfig
from hother.streamblocks_examples.blocks.agent import FileOperations

# =============================================================================
# Timing Utilities
# =============================================================================


@contextmanager
def assert_completes_within(seconds: float) -> Generator[None]:
    """Context manager to assert that code completes within a time limit.

    Args:
        seconds: Maximum allowed execution time

    Raises:
        AssertionError: If execution takes longer than specified
    """
    start = time.monotonic()
    yield
    elapsed = time.monotonic() - start
    assert elapsed < seconds, f"Took {elapsed:.2f}s, expected < {seconds}s"


# =============================================================================
# Syntax Fixtures
# =============================================================================


@pytest.fixture
def delimiter_preamble_syntax() -> DelimiterPreambleSyntax:
    """Create a DelimiterPreambleSyntax instance."""
    return DelimiterPreambleSyntax()


@pytest.fixture
def delimiter_frontmatter_syntax() -> DelimiterFrontmatterSyntax:
    """Create a DelimiterFrontmatterSyntax instance."""
    return DelimiterFrontmatterSyntax()


# =============================================================================
# Registry Fixtures
# =============================================================================


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
def clean_registry(delimiter_preamble_syntax: DelimiterPreambleSyntax) -> Registry:
    """Provide an isolated, empty registry for each test."""
    return Registry(syntax=delimiter_preamble_syntax)


# =============================================================================
# Processor Fixtures
# =============================================================================


@pytest.fixture
def default_config() -> ProcessorConfig:
    """Default processor configuration for tests."""
    return ProcessorConfig(emit_text_deltas=False)


@pytest.fixture
def verbose_config() -> ProcessorConfig:
    """Verbose processor configuration with all events enabled."""
    return ProcessorConfig(
        emit_text_deltas=True,
        emit_original_events=True,
        emit_section_end_events=True,
    )


@pytest.fixture
def processor(file_operations_registry: Registry, default_config: ProcessorConfig) -> StreamBlockProcessor:
    """Create a StreamBlockProcessor with FileOperations."""
    return StreamBlockProcessor(file_operations_registry, config=default_config)


@pytest.fixture
def frontmatter_processor(frontmatter_registry: Registry, default_config: ProcessorConfig) -> StreamBlockProcessor:
    """Create a StreamBlockProcessor with frontmatter syntax."""
    return StreamBlockProcessor(frontmatter_registry, config=default_config)


# =============================================================================
# Stream Fixtures
# =============================================================================


@pytest.fixture
def mock_stream() -> Callable[[str], AsyncIterator[str]]:
    """Factory fixture for creating mock async streams from text."""

    async def _create(text: str) -> AsyncIterator[str]:
        for line in text.split("\n"):
            yield line + "\n"

    return _create


@pytest.fixture
def chunked_stream() -> Callable[[str, int], AsyncIterator[str]]:
    """Factory fixture for creating mock async streams with custom chunk sizes."""

    async def _create(text: str, chunk_size: int = 10) -> AsyncIterator[str]:
        for i in range(0, len(text), chunk_size):
            yield text[i : i + chunk_size]

    return _create


# =============================================================================
# Sample Data Fixtures
# =============================================================================


@pytest.fixture
def sample_block_text() -> str:
    """Sample block text for testing."""
    return """!!block01:files_operations
src/main.py:C
src/utils.py:E
!!end
"""


@pytest.fixture
def sample_frontmatter_text() -> str:
    """Sample frontmatter block text for testing."""
    return """!!start
---
id: test_block
block_type: files_operations
---
src/main.py:C
!!end
"""


# =============================================================================
# Event Collection Fixtures
# =============================================================================


@pytest.fixture
def event_collector() -> Callable[[], dict[str, list[Any]]]:
    """Factory fixture for collecting events by type during tests."""

    def _create() -> dict[str, list[Any]]:
        return {
            "all": [],
            "block_start": [],
            "block_end": [],
            "block_error": [],
            "text_content": [],
            "text_delta": [],
        }

    return _create
