"""File operations content models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .base import BaseContent


class FileOperation(BaseModel):
    """Represents a single file operation."""

    action: Literal["create", "edit", "delete"] = Field(
        ..., description="The type of file operation"
    )
    path: str = Field(..., description="Path to the file")


class FileOperationsContent(BaseContent):
    """Content model for file operations blocks."""

    operations: list[FileOperation] = Field(
        default_factory=list, description="List of file operations"
    )

    @classmethod
    def parse(cls, text: str) -> FileOperationsContent:
        """Parse file operations from text.

        Expected format: "path:action" per line where action is C/E/D.
        - C = create
        - E = edit
        - D = delete

        Args:
            text: Raw text containing file operations

        Returns:
            Parsed FileOperationsContent instance

        Raises:
            ValueError: If text contains invalid operations
        """
        operations = []

        for line in text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue

            # Split on last colon to handle paths with colons
            if ":" not in line:
                raise ValueError(f"Invalid file operation format: {line}")

            # Find the last colon
            last_colon_idx = line.rfind(":")
            path = line[:last_colon_idx].strip()
            action_code = line[last_colon_idx + 1 :].strip().upper()

            # Map action codes
            action_map = {"C": "create", "E": "edit", "D": "delete"}

            if action_code not in action_map:
                raise ValueError(f"Unknown action code: {action_code}")

            operations.append(FileOperation(action=action_map[action_code], path=path))

        return cls(operations=operations)


class FileOperationsMetadata(BaseModel):
    """Metadata model for file operations blocks."""

    id: str = Field(..., description="Block identifier")
    block_type: Literal["files_operations"] = Field(
        default="files_operations", description="Type of block"
    )
    description: str | None = Field(
        default=None, description="Optional description of the operations"
    )
