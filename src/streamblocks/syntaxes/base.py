"""Base module for syntax framework.

This module provides the core imports and foundational elements
for building syntax parsers.
"""

from streamblocks.core.models import BlockCandidate
from streamblocks.core.types import (
    BlockState,
    BlockSyntax,
    DetectionResult,
    ParseResult,
    TContent,
    TMetadata,
)

__all__ = [
    "BlockSyntax",
    "BlockState",
    "BlockCandidate",
    "DetectionResult",
    "ParseResult",
    "TMetadata",
    "TContent",
]
