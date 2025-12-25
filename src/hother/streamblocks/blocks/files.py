"""File operations content models."""

from __future__ import annotations

from typing import Final, Literal

from pydantic import BaseModel, Field

from hother.streamblocks.core.models import Block
from hother.streamblocks.core.types import BaseContent, BaseMetadata

ActionLiteral = Literal["create", "edit", "delete"]

# Action code mapping with proper typing
ACTION_MAP: Final[dict[str, ActionLiteral]] = {"C": "create", "E": "edit", "D": "delete"}


class FileOperation(BaseModel):
    """Single file operation."""

    action: ActionLiteral
    path: str


class FileOperationsContent(BaseContent):
    """Content model for file operations blocks."""

    operations: list[FileOperation] = Field(default_factory=list[FileOperation])

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

            if action.upper() not in ACTION_MAP:
                msg = f"Unknown action: {action}"
                raise ValueError(msg)

            action_literal = ACTION_MAP[action.upper()]

            operations.append(
                FileOperation(
                    action=action_literal,
                    path=path.strip(),
                )
            )

        return cls(raw_content=raw_text, operations=operations)


class FileOperationsMetadata(BaseMetadata):
    """Metadata for file operations blocks."""

    block_type: Literal["files_operations"] = "files_operations"
    description: str | None = None


class FileContentMetadata(BaseMetadata):
    """Metadata for file content blocks."""

    block_type: Literal["file_content"] = "file_content"
    file: str  # Path to the file
    description: str | None = None


class FileContentContent(BaseContent):
    """Content model for file content blocks."""

    # The raw_content field from BaseContent contains the file contents

    @classmethod
    def parse(cls, raw_text: str) -> FileContentContent:
        """Parse file content - just stores the raw text."""
        return cls(raw_content=raw_text)


# Block type definitions


class FileOperations(Block[FileOperationsMetadata, FileOperationsContent]):
    """File operations block."""


class FileContent(Block[FileContentMetadata, FileContentContent]):
    """File content block."""
