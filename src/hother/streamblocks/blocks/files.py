"""File operations content models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from hother.streamblocks.core.models import BaseContent, BaseMetadata, BlockConfig


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
        path/to/delete.py:D

        Where C=create, E=edit, D=delete
        """
        operations: list[FileOperation] = []
        for line in raw_text.strip().split("\n"):
            if not line.strip():
                continue

            if ":" not in line:
                msg = f"Invalid format: {line}"
                raise ValueError(msg)

            path, action = line.rsplit(":", 1)
            action_map = {"C": "create", "E": "edit", "D": "delete"}

            if action.upper() not in action_map:
                msg = f"Unknown action: {action}"
                raise ValueError(msg)

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

    def __init__(self, **data: object) -> None:
        # Set default block_type if not provided
        if "block_type" not in data:
            data["block_type"] = "files_operations"
        super().__init__(**data)


class FileContentMetadata(BaseMetadata):
    """Metadata for file content blocks."""

    file: str  # Path to the file
    description: str | None = None

    def __init__(self, **data: object) -> None:
        # Set default block_type if not provided
        if "block_type" not in data:
            data["block_type"] = "file_content"
        super().__init__(**data)


class FileContentContent(BaseContent):
    """Content model for file content blocks."""

    # The raw_content field from BaseContent contains the file contents

    @classmethod
    def parse(cls, raw_text: str) -> FileContentContent:
        """Parse file content - just stores the raw text."""
        return cls(raw_content=raw_text)


# Block configuration classes


class FileOperations(BlockConfig):
    """File operations block configuration."""

    __metadata_class__ = FileOperationsMetadata
    __content_class__ = FileOperationsContent


class FileContent(BlockConfig):
    """File content block configuration."""

    __metadata_class__ = FileContentMetadata
    __content_class__ = FileContentContent
