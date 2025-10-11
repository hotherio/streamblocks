"""Stream adapters for converting various chunk formats to text.

This module provides adapters for extracting text from different
streaming formats (Gemini, OpenAI, Anthropic, etc.) to enable
unified processing by StreamBlocks.
"""

from __future__ import annotations

from hother.streamblocks.adapters.base import StreamAdapter
from hother.streamblocks.adapters.detection import AdapterDetector
from hother.streamblocks.adapters.providers import (
    AnthropicAdapter,
    AttributeAdapter,
    CallableAdapter,
    GeminiAdapter,
    IdentityAdapter,
    OpenAIAdapter,
)

__all__ = [
    "AdapterDetector",
    "AnthropicAdapter",
    "AttributeAdapter",
    "CallableAdapter",
    "GeminiAdapter",
    "IdentityAdapter",
    "OpenAIAdapter",
    "StreamAdapter",
]
