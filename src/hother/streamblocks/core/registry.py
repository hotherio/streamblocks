"""Type-specific registry for StreamBlocks."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeVar

from pydantic import BaseModel

if TYPE_CHECKING:
    from hother.streamblocks.core.protocols import BlockSyntax

type BlockType = str
type ValidatorFunc = Callable[[BaseModel, BaseModel], bool]

# Type variable for syntax types
TSyntax = TypeVar("TSyntax", bound="BlockSyntax[Any, Any]")


class Registry[TSyntax: "BlockSyntax[Any, Any]"]:
    """Type-specific registry for a single syntax type.

    This registry holds exactly one syntax instance and its associated validators.
    Each registry is parameterized by the syntax type, ensuring type safety.

    Example:
        >>> syntax = DelimiterPreambleSyntax(...)
        >>> registry = Registry(syntax)
        >>> registry.add_validator("files_operations", my_validator)
    """

    def __init__(self, syntax: TSyntax) -> None:
        """Initialize registry with a single syntax instance.

        Args:
            syntax: The syntax instance for this registry
        """
        self._syntax = syntax
        self._validators: dict[BlockType, list[ValidatorFunc]] = {}

    @property
    def syntax(self) -> TSyntax:
        """Get the syntax instance."""
        return self._syntax

    def add_validator(
        self,
        block_type: BlockType,
        validator: ValidatorFunc,
    ) -> None:
        """Add a validator for a block type.

        Args:
            block_type: Type of block to validate
            validator: Function that validates metadata and content
        """
        if block_type not in self._validators:
            self._validators[block_type] = []
        self._validators[block_type].append(validator)

    def validate_block(
        self,
        block_type: BlockType,
        metadata: BaseModel,
        content: BaseModel,
    ) -> bool:
        """Run all validators for a block type.

        Args:
            block_type: Type of block being validated
            metadata: Block metadata to validate
            content: Block content to validate

        Returns:
            True if all validators pass
        """
        validators = self._validators.get(block_type, [])
        return all(v(metadata, content) for v in validators)


# Backward compatibility alias (will be removed in future versions)
BlockRegistry = Registry
