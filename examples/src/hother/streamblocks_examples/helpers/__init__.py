"""Reusable helpers for StreamBlocks examples."""

from hother.streamblocks_examples.helpers.handlers import collect_blocks, print_events
from hother.streamblocks_examples.helpers.setup import default_processor, default_registry

# Import simulator helpers (may not be available if cancelable not installed)
try:
    from hother.streamblocks_examples.helpers.simulator import (
        SIMULATOR_AVAILABLE,
        StreamConfig,
        StreamPresets,
        chunked_text_stream,
        simple_text_stream,
        simulated_stream,
    )
except ImportError:
    SIMULATOR_AVAILABLE = False
    simulated_stream = None  # type: ignore[misc, assignment]
    chunked_text_stream = None  # type: ignore[misc, assignment]
    simple_text_stream = None  # type: ignore[misc, assignment]
    StreamPresets = None  # type: ignore[misc, assignment]
    StreamConfig = None  # type: ignore[misc, assignment]

__all__ = [
    "SIMULATOR_AVAILABLE",
    "StreamConfig",
    "StreamPresets",
    "chunked_text_stream",
    "collect_blocks",
    "default_processor",
    "default_registry",
    "print_events",
    "simple_text_stream",
    "simulated_stream",
]
