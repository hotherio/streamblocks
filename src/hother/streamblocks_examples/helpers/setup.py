"""Common setup functions for examples."""

from hother.streamblocks import DelimiterPreambleSyntax, Registry, StreamBlockProcessor
from hother.streamblocks.core.processor import ProcessorConfig
from hother.streamblocks_examples.blocks.agent.files import FileOperations


def default_registry() -> Registry:
    """Create a default registry with common block types.

    Returns:
        Registry configured with DelimiterPreambleSyntax and FileOperations.
    """
    syntax = DelimiterPreambleSyntax()
    registry = Registry(syntax=syntax)
    registry.register("files_operations", FileOperations)
    return registry


def default_processor(
    registry: Registry | None = None,
    lines_buffer: int = 5,
) -> StreamBlockProcessor:
    """Create a default processor.

    Args:
        registry: Registry to use. If None, creates a default one.
        lines_buffer: Number of lines to buffer.

    Returns:
        Configured StreamBlockProcessor.
    """
    if registry is None:
        registry = default_registry()

    config = ProcessorConfig(lines_buffer=lines_buffer)
    return StreamBlockProcessor(registry, config=config)
