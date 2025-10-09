"""Memory content models for storing and recalling context."""

from __future__ import annotations

from typing import Any, Literal

import yaml

from hother.streamblocks.core.models import Block
from hother.streamblocks.core.types import BaseContent, BaseMetadata


class MemoryMetadata(BaseMetadata):
    """Metadata for memory/context blocks."""

    memory_type: Literal["store", "recall", "update", "delete", "list"]
    key: str
    ttl_seconds: int | None = None
    namespace: str = "default"


class MemoryContent(BaseContent):
    """Content for memory operations."""

    value: Any | None = None
    previous_value: Any | None = None
    keys: list[str] | None = None  # For list operations

    @classmethod
    def parse(cls, raw_text: str) -> MemoryContent:
        """Parse YAML value for memory operations."""
        if not raw_text.strip():
            return cls(raw_content=raw_text)

        try:
            data: dict[str, Any] = yaml.safe_load(raw_text) or {}
            if "value" in data:
                return cls(raw_content=raw_text, **data)
            # If not a dict with 'value' key, treat entire content as value
            return cls(raw_content=raw_text, value=data)
        except yaml.YAMLError:
            # If YAML parsing fails, treat as plain text value
            return cls(raw_content=raw_text, value=raw_text.strip())


# Block type alias
Memory = Block[MemoryMetadata, MemoryContent]
