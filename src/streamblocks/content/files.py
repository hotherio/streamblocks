"""File operations content models."""

from __future__ import annotations

from enum import StrEnum
from typing import Final, Literal

from pydantic import BaseModel, Field

from .base import BaseContent

type _ActionName = Literal["create", "edit", "delete"]

# Mapping from action codes to action names (type-checked by mypy)
_ACTION_MAP: Final[dict[str, _ActionName]] = {
    "C": "create",
    "E": "edit",
    "D": "delete",
}


class ActionCode(StrEnum):
    """Action codes for file operations."""

    CREATE = "C"
    EDIT = "E"
    DELETE = "D"

    @property
    def action_name(self) -> _ActionName:
        """Get the action name for this code."""
        return _ACTION_MAP[self.value]


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
            stripped_line = line.strip()
            if not stripped_line:
                continue

            # Split on last colon to handle paths with colons
            if ":" not in stripped_line:
                raise ValueError(f"Invalid file operation format: {stripped_line}")

            # Find the last colon
            last_colon_idx = stripped_line.rfind(":")
            path = stripped_line[:last_colon_idx].strip()
            action_code_str = stripped_line[last_colon_idx + 1 :].strip().upper()

            # Validate and get action code
            try:
                action_code = ActionCode(action_code_str)
            except ValueError:
                raise ValueError(f"Unknown action code: {action_code_str}") from None

            operations.append(FileOperation(action=action_code.action_name, path=path))

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
