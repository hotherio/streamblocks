"""Type-specific registry for StreamBlocks."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from hother.streamblocks.syntaxes.models import get_syntax_instance

if TYPE_CHECKING:
    from hother.streamblocks.core.models import Block, ExtractedBlock
    from hother.streamblocks.core.types import BaseContent, BaseMetadata
    from hother.streamblocks.syntaxes.base import BaseSyntax
    from hother.streamblocks.syntaxes.models import Syntax

type BlockType = str
type ValidatorFunc = Callable[[ExtractedBlock], bool]


class Registry:
    """Type-specific registry for a single syntax type.

    This registry holds exactly one syntax instance and maps block types to block classes.

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
        *,
        syntax: Syntax | BaseSyntax,
        blocks: dict[str, type[Block[BaseMetadata, BaseContent]]] | None = None,
    ) -> None:
        """Initialize registry with a single syntax instance.

        Args:
            syntax: The syntax instance for this registry
            blocks: Optional dict of block_type -> block_class for bulk registration
        """
        self._syntax = get_syntax_instance(syntax=syntax)
        self._block_classes: dict[BlockType, type[Block[BaseMetadata, BaseContent]]] = {}
        self._validators: dict[BlockType, list[ValidatorFunc]] = {}

        # Bulk register blocks if provided
        if blocks:
            for block_type, block_class in blocks.items():
                self.register(block_type, block_class)

    @property
    def syntax(self) -> BaseSyntax:
        """Get the syntax instance."""
        return self._syntax

    def register(
        self,
        name: str,
        block_class: type[Block[BaseMetadata, BaseContent]],
        validators: list[ValidatorFunc] | None = None,
    ) -> None:
        """Register a block class for a block type.

        Args:
            name: Block type name (e.g., "files_operations", "patch")
            block_class: Block class inheriting from Block[M, C]
            validators: Optional list of validator functions for this block type
        """
        self._block_classes[name] = block_class

        # Add validators if provided
        if validators:
            for validator in validators:
                self.add_validator(name, validator)

    def get_block_class(self, block_type: str) -> type[Block[BaseMetadata, BaseContent]] | None:
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
            validator: Function that validates a block
        """
        if block_type not in self._validators:
            self._validators[block_type] = []
        self._validators[block_type].append(validator)

    def validate_block(
        self,
        block: ExtractedBlock,
    ) -> bool:
        """Run all validators for a block.

        Args:
            block: Extracted block to validate

        Returns:
            True if all validators pass
        """
        block_type = getattr(block.metadata, "block_type", None)
        if not block_type:
            return True

        validators = self._validators.get(block_type, [])
        return all(v(block) for v in validators)
