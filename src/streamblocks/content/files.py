"""File operations content models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from streamblocks.core.models import BaseContent, BaseMetadata


class FileOperation(BaseModel):
    """Single file operation."""

    action: Literal["create", "edit", "delete"]
    path: str


class FileOperationsContent(BaseContent):
    """Content model for file operations blocks."""

    operations: list[FileOperation] = Field(default_factory=list)

    @classmethod
    def parse(cls, raw_text: str) -> FileOperationsContent:
        """Parse file operations from raw text.

        Expected format:
        path/to/file.py:C
        path/to/other.py:E
        path/to/delete.py:D

        Where C=create, E=edit, D=delete
        """
        operations = []
        for line in raw_text.strip().split("\n"):
            if not line.strip():
                continue

            if ":" not in line:
                raise ValueError(f"Invalid format: {line}")

            path, action = line.rsplit(":", 1)
            action_map = {"C": "create", "E": "edit", "D": "delete"}

            if action.upper() not in action_map:
                raise ValueError(f"Unknown action: {action}")

            operations.append(
                FileOperation(
                    action=action_map[action.upper()],  # type: ignore[arg-type]
                    path=path.strip(),
                )
            )

        return cls(raw_content=raw_text, operations=operations)


class FileOperationsMetadata(BaseMetadata):
    """Metadata for file operations blocks."""
    
    # Additional fields beyond BaseMetadata
    type: Literal["files_operations"] = "files_operations"  # Alias for compatibility
    description: str | None = None
    
    def __init__(self, **data):
        # Set default block_type if not provided
        if "block_type" not in data:
            data["block_type"] = "files_operations"
        super().__init__(**data)
