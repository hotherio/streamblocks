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

    This registry holds exactly one syntax instance and maps block types to block classes.
    Each registry is parameterized by the syntax type, ensuring type safety.

    Example:
        >>> syntax = DelimiterPreambleSyntax(name="my_syntax")
        >>> registry = Registry(syntax)
        >>> registry.register("files_operations", FileOperations, validators=[my_validator])
        >>> registry.register("patch", Patch)

        Or with bulk registration:
        >>> registry = Registry(
        ...     syntax=syntax,
        ...     blocks={
        ...         "files_operations": FileOperations,
        ...         "patch": Patch,
        ...     }
        ... )
        >>> registry.add_validator("files_operations", my_validator)
    """

    def __init__(
        self,
        syntax: TSyntax,
        blocks: dict[str, type[Any]] | None = None,
    ) -> None:
        """Initialize registry with a single syntax instance.

        Args:
            syntax: The syntax instance for this registry
            blocks: Optional dict of block_type -> block_class for bulk registration
        """
        self._syntax = syntax
        self._block_classes: dict[BlockType, type[Any]] = {}
        self._validators: dict[BlockType, list[ValidatorFunc]] = {}

        # Bulk register blocks if provided
        if blocks:
            for block_type, block_class in blocks.items():
                self.register(block_type, block_class)

    @property
    def syntax(self) -> TSyntax:
        """Get the syntax instance."""
        return self._syntax

    def register(
        self,
        name: str,
        block_class: type[Any],
        validators: list[ValidatorFunc] | None = None,
    ) -> None:
        """Register a block class for a block type.

        Args:
            name: Block type name (e.g., "files_operations", "patch")
            block_class: BlockDefinition class with __metadata_class__ and __content_class__
            validators: Optional list of validator functions for this block type
        """
        self._block_classes[name] = block_class

        # Add validators if provided
        if validators:
            for validator in validators:
                self.add_validator(name, validator)

    def get_block_class(self, block_type: str) -> type[Any] | None:
        """Get the block class for a given block type.

        Args:
            block_type: The block type to look up

        Returns:
            The registered block class, or None if not found
        """
        return self._block_classes.get(block_type)

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
