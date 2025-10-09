"""Tool calling content models for executing external tools."""

from __future__ import annotations

from typing import Any

import yaml
from pydantic import Field

from hother.streamblocks.core.models import Block
from hother.streamblocks.core.types import BaseContent, BaseMetadata


class ToolCallMetadata(BaseMetadata):
    """Metadata for tool calling blocks."""

    tool_name: str
    async_call: bool = False
    timeout: float | None = None
    description: str | None = None


class ToolCallContent(BaseContent):
    """Content for tool calling blocks - contains parameters as YAML."""

    parameters: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def parse(cls, raw_text: str) -> ToolCallContent:
        """Parse YAML parameters."""
        try:
            params: dict[str, Any] = yaml.safe_load(raw_text) or {}
        except yaml.YAMLError as e:
            msg = f"Invalid YAML parameters: {e}"
            raise ValueError(msg) from e

        return cls(raw_content=raw_text, parameters=params)


# Block type alias
ToolCall = Block[ToolCallMetadata, ToolCallContent]
