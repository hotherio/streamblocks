"""File operations content models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from hother.streamblocks.core.models import Block
from hother.streamblocks.core.types import BaseContent, BaseMetadata


class FileOperation(BaseModel):
    """Single file operation."""

    action: Literal["create", "edit", "delete"]
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

    # Override block_type with specific literal and default
    block_type: Literal["files_operations"] = "files_operations"  # type: ignore[assignment]
    description: str | None = Field(default=None, description="Why are you performing these operations?")


class FileContentMetadata(BaseMetadata):
    """Metadata for file content blocks."""

    block_type: Literal["file_content"] = "file_content"  # type: ignore[assignment]
    file: str  # Path to the file
    description: str | None = Field(default=None, description="Why do you need the content of this file?")


class FileContentContent(BaseContent):
    """Content model for file content blocks."""

    # The raw_content field from BaseContent contains the file contents

    @classmethod
    def parse(cls, raw_text: str) -> FileContentContent:
        """Parse file content - just stores the raw text."""
        return cls(raw_content=raw_text)


# Block type definitions


class FileOperations(Block[FileOperationsMetadata, FileOperationsContent]):
    """Manage file creation, editing, and deletion operations.

    Use this block when you need to create, edit, or delete multiple files
    in a single operation.
    """

    __examples__ = [
        {
            "metadata": {
                "id": "f1",
                "block_type": "files_operations",
                "description": "Create Python application structure",
            },
            "content": {
                "operations": [
                    {"action": "create", "path": "src/main.py"},
                    {"action": "create", "path": "src/utils.py"},
                    {"action": "create", "path": "tests/test_main.py"},
                ],
            },
        },
        {
            "metadata": {
                "id": "f2",
                "block_type": "files_operations",
                "description": "Remove deprecated files",
            },
            "content": {
                "operations": [
                    {"action": "delete", "path": "legacy/old_module.py"},
                    {"action": "delete", "path": "deprecated.py"},
                ],
            },
        },
        {
            "metadata": {
                "id": "f3",
                "block_type": "files_operations",
            },
            "content": {
                "operations": [
                    {"action": "create", "path": "config.yaml"},
                    {"action": "edit", "path": "settings.py"},
                ],
            },
        },
    ]


class FileContent(Block[FileContentMetadata, FileContentContent]):
    """File content block."""
