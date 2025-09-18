"""Registry for block syntaxes and validators."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

if TYPE_CHECKING:
    from streamblocks.core.protocols import BlockSyntax

type BlockType = str
type ValidatorFunc = Callable[[BaseModel, BaseModel], bool]


class BlockRegistry:
    """Registry for block syntaxes and parsers."""

    def __init__(self) -> None:
        """Initialize an empty registry."""
        self._syntaxes: dict[str, BlockSyntax[Any, Any]] = {}
        self._block_types: dict[BlockType, list[BlockSyntax[Any, Any]]] = {}
        self._validators: dict[BlockType, list[ValidatorFunc]] = {}
        self._priority_order: list[str] = []  # Syntax names in priority order
        self._syntax_priorities: dict[str, int] = {}  # Syntax name to priority

    def register_syntax(
        self,
        syntax: BlockSyntax[Any, Any],
        block_types: list[BlockType] | None = None,
        priority: int = 100,
    ) -> None:
        """Register a syntax parser.

        Args:
            syntax: The syntax implementation
            block_types: Block types this syntax can handle
            priority: Lower number = higher priority for detection
        """
        if syntax.name in self._syntaxes:
            raise ValueError(f"Syntax '{syntax.name}' already registered")

        self._syntaxes[syntax.name] = syntax
        self._syntax_priorities[syntax.name] = priority

        # Map block types to syntaxes
        if block_types:
            for bt in block_types:
                if bt not in self._block_types:
                    self._block_types[bt] = []
                self._block_types[bt].append(syntax)

        # Update priority order
        self._update_priority_order()

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

    def get_syntaxes(self) -> list[BlockSyntax[Any, Any]]:
        """Get all registered syntaxes in priority order."""
        return [self._syntaxes[name] for name in self._priority_order if name in self._syntaxes]

    def get_syntax_by_name(self, name: str) -> BlockSyntax[Any, Any] | None:
        """Get a specific syntax by name."""
        return self._syntaxes.get(name)

    def get_syntaxes_for_block_type(self, block_type: BlockType) -> list[BlockSyntax[Any, Any]]:
        """Get syntaxes that can handle a specific block type."""
        syntaxes = self._block_types.get(block_type, [])
        # Sort by priority
        return sorted(syntaxes, key=lambda s: self._syntax_priorities.get(s.name, 100))

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

    def _update_priority_order(self) -> None:
        """Update the priority order list."""
        # Sort syntax names by priority (lower number = higher priority)
        self._priority_order = sorted(self._syntaxes.keys(), key=lambda name: self._syntax_priorities.get(name, 100))
