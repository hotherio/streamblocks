"""Visualization content models for creating charts, diagrams, and tables."""

from __future__ import annotations

from typing import Any, Literal

import yaml

from hother.streamblocks.core.models import Block
from hother.streamblocks.core.types import BaseContent, BaseMetadata


class VisualizationMetadata(BaseMetadata):
    """Metadata for visualization blocks."""

    viz_type: Literal["chart", "diagram", "table", "code", "ascii_art"]
    title: str
    format: Literal["ascii", "markdown", "html"] = "markdown"
    width: int | None = None
    height: int | None = None


class VisualizationContent(BaseContent):
    """Content for visualization blocks."""

    data: dict[str, Any]
    rendered: str | None = None

    @classmethod
    def parse(cls, raw_text: str) -> VisualizationContent:
        """Parse YAML data for visualization."""
        try:
            data: dict[str, Any] = yaml.safe_load(raw_text) or {}
        except yaml.YAMLError as e:
            msg = f"Invalid YAML data: {e}"
            raise ValueError(msg) from e

        return cls(raw_content=raw_text, data=data)


# Block type alias
Visualization = Block[VisualizationMetadata, VisualizationContent]
