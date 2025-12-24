"""Stream adapters for bidirectional protocol transformation.

This module provides the adapter system for transforming between
different input and output protocols.

Key Components:
- EventCategory: Categorize events for routing (TEXT_CONTENT, PASSTHROUGH, SKIP)
- InputProtocolAdapter: Protocol for input transformation
- OutputProtocolAdapter: Protocol for output transformation
- InputAdapterRegistry: Auto-detection of input adapters

Example:
    >>> from hother.streamblocks.adapters import EventCategory, InputAdapterRegistry
    >>> from hother.streamblocks.adapters.input import IdentityInputAdapter
    >>> from hother.streamblocks.adapters.output import StreamBlocksOutputAdapter
"""

from __future__ import annotations

from hother.streamblocks.adapters.categories import EventCategory
from hother.streamblocks.adapters.detection import (
    InputAdapterRegistry,
    detect_input_adapter,
)
from hother.streamblocks.adapters.protocols import (
    BidirectionalAdapter,
    InputProtocolAdapter,
    OutputProtocolAdapter,
)

__all__ = [
    "BidirectionalAdapter",
    "EventCategory",
    "InputAdapterRegistry",
    "InputProtocolAdapter",
    "OutputProtocolAdapter",
    "detect_input_adapter",
]
