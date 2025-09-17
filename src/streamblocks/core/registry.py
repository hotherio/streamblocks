"""Block registry for managing syntax parsers."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .types import BlockSyntax

# Type alias for block type identifiers
BlockType = str


class BlockRegistry:
    """Registry for managing block syntax parsers.

    The BlockRegistry maintains a collection of BlockSyntax instances,
    organizing them by name, block types, and priority order. It provides
    methods for registering new syntaxes and retrieving them in priority order.

    Attributes:
        _syntaxes: Mapping from syntax name to BlockSyntax instance
        _block_types: Mapping from block type to list of syntaxes that handle it
        _validators: Mapping from block type to list of validation functions
        _priority_order: List of syntax names in priority order
    """

    def __init__(self) -> None:
        """Initialize an empty registry."""
        self._syntaxes: dict[str, BlockSyntax] = {}
        self._block_types: dict[BlockType, list[BlockSyntax]] = {}
        self._validators: dict[BlockType, list[Callable]] = {}
        self._priority_order: list[str] = []

    def register_syntax(
        self,
        syntax: BlockSyntax,
        block_types: list[BlockType] | None = None,
        priority: int = 50,
    ) -> None:
        """Register a new syntax parser.

        Args:
            syntax: The BlockSyntax instance to register
            block_types: List of block types this syntax handles (optional)
            priority: Priority for this syntax (lower = higher priority, default 50)

        Raises:
            ValueError: If a syntax with the same name is already registered
        """
        name = syntax.name

        # Check for duplicate registration
        if name in self._syntaxes:
            raise ValueError(f"Syntax '{name}' is already registered")

        # Store syntax reference
        self._syntaxes[name] = syntax

        # Register block types if provided
        if block_types:
            for block_type in block_types:
                if block_type not in self._block_types:
                    self._block_types[block_type] = []
                self._block_types[block_type].append(syntax)

        # Add to priority order
        # This is a simplified version - in a full implementation we'd sort by priority
        self._priority_order.append(name)

    def get_syntaxes(self) -> list[BlockSyntax]:
        """Get all registered syntaxes in priority order.

        Returns:
            List of BlockSyntax instances ordered by priority
        """
        return [self._syntaxes[name] for name in self._priority_order]

    def get_syntax_by_name(self, name: str) -> BlockSyntax | None:
        """Get a specific syntax by name.

        Args:
            name: The name of the syntax to retrieve

        Returns:
            The BlockSyntax instance if found, None otherwise
        """
        return self._syntaxes.get(name)

    def get_syntaxes_for_block_type(self, block_type: BlockType) -> list[BlockSyntax]:
        """Get all syntaxes that handle a specific block type.

        Args:
            block_type: The block type to query

        Returns:
            List of BlockSyntax instances that handle this block type
        """
        return self._block_types.get(block_type, [])

    # Placeholder methods for future tracks
    def register_validator(self, block_type: BlockType, validator: Callable) -> None:
        """Register a validator for a block type (placeholder for Track 7)."""
        pass

    def validate_block(self, block_type: BlockType, metadata: object, content: object) -> bool:
        """Validate a block (placeholder for Track 7)."""
        return True

    def unregister_syntax(self, name: str) -> None:
        """Unregister a syntax (placeholder for Track 7)."""
        pass

    def clear(self) -> None:
        """Clear all registered syntaxes (placeholder for Track 7)."""
        pass
