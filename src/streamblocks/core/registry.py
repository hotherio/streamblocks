"""Block registry for managing syntax parsers.

The registry provides a centralized location for managing block syntax
parsers, with support for:

- Priority-based ordering
- Block type associations
- Syntax validation
- Performance optimizations
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

if TYPE_CHECKING:
    from .types import BlockSyntax

# Type alias for block type identifiers
BlockType = str

# Type for validator functions
ValidatorFunc = Callable[[BaseModel, BaseModel], bool]


@dataclass
class SyntaxEntry:
    """Internal representation of a registered syntax."""

    syntax: BlockSyntax[Any, Any]
    priority: int
    block_types: list[BlockType]
    opening_pattern: re.Pattern[str] | None = None
    closing_pattern: re.Pattern[str] | None = None


class BlockRegistry:
    """Registry for managing block syntax parsers.

    The BlockRegistry maintains a collection of BlockSyntax instances,
    organizing them by name, block types, and priority order. It provides
    methods for registering new syntaxes and retrieving them in priority order.

    Enhanced features:
    - Priority-based ordering with automatic sorting
    - Pattern caching for performance
    - Block type associations
    - Custom validators per block type
    - Conflict detection
    """

    def __init__(self) -> None:
        """Initialize an empty registry."""
        self._entries: dict[str, SyntaxEntry] = {}
        self._block_types: dict[BlockType, list[str]] = defaultdict(list)
        self._validators: dict[BlockType, list[ValidatorFunc]] = defaultdict(list)
        self._priority_sorted: bool = False

    def register_syntax(
        self,
        syntax: BlockSyntax[Any, Any],
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
        if name in self._entries:
            raise ValueError(f"Syntax '{name}' is already registered")

        # Get block types from syntax if not provided
        if block_types is None:
            block_types = syntax.get_block_type_hints()

        # Compile patterns if provided
        opening_pattern = None
        closing_pattern = None

        opening_str = syntax.get_opening_pattern()
        if opening_str:
            try:
                opening_pattern = re.compile(opening_str)
            except re.error as e:
                raise ValueError(f"Invalid opening pattern for '{name}': {e}") from e

        closing_str = syntax.get_closing_pattern()
        if closing_str:
            try:
                closing_pattern = re.compile(closing_str)
            except re.error as e:
                raise ValueError(f"Invalid closing pattern for '{name}': {e}") from e

        # Create entry
        entry = SyntaxEntry(
            syntax=syntax,
            priority=priority,
            block_types=block_types,
            opening_pattern=opening_pattern,
            closing_pattern=closing_pattern,
        )

        # Store entry
        self._entries[name] = entry

        # Update block type mappings
        for block_type in block_types:
            self._block_types[block_type].append(name)

        # Mark that priority order needs updating
        self._priority_sorted = False

    def _ensure_sorted(self) -> None:
        """Ensure entries are sorted by priority."""
        if not self._priority_sorted:
            # Sort entries by priority (lower number = higher priority)
            sorted_entries = sorted(
                self._entries.items(),
                key=lambda x: (x[1].priority, x[0]),  # Sort by priority, then name
            )
            self._entries = dict(sorted_entries)
            self._priority_sorted = True

    def get_syntaxes(self) -> list[BlockSyntax[Any, Any]]:
        """Get all registered syntaxes in priority order.

        Returns:
            List of BlockSyntax instances ordered by priority
        """
        self._ensure_sorted()
        return [entry.syntax for entry in self._entries.values()]

    def get_syntax_by_name(self, name: str) -> BlockSyntax[Any, Any] | None:
        """Get a specific syntax by name.

        Args:
            name: The name of the syntax to retrieve

        Returns:
            The BlockSyntax instance if found, None otherwise
        """
        entry = self._entries.get(name)
        return entry.syntax if entry else None

    def get_syntaxes_for_block_type(self, block_type: BlockType) -> list[BlockSyntax[Any, Any]]:
        """Get all syntaxes that handle a specific block type.

        Args:
            block_type: The block type to query

        Returns:
            List of BlockSyntax instances that handle this block type
        """
        self._ensure_sorted()
        syntax_names = self._block_types.get(block_type, [])
        return [self._entries[name].syntax for name in syntax_names if name in self._entries]

    # Enhanced methods

    def get_entries(self) -> dict[str, SyntaxEntry]:
        """Get all syntax entries for debugging/inspection.

        Returns:
            Dictionary mapping syntax names to their entries
        """
        self._ensure_sorted()
        return self._entries.copy()

    def get_opening_patterns(self) -> dict[str, re.Pattern[str]]:
        """Get all compiled opening patterns.

        Returns:
            Dictionary mapping syntax names to opening patterns
        """
        return {
            name: entry.opening_pattern
            for name, entry in self._entries.items()
            if entry.opening_pattern
        }

    def get_closing_patterns(self) -> dict[str, re.Pattern[str]]:
        """Get all compiled closing patterns.

        Returns:
            Dictionary mapping syntax names to closing patterns
        """
        return {
            name: entry.closing_pattern
            for name, entry in self._entries.items()
            if entry.closing_pattern
        }

    def has_syntax(self, name: str) -> bool:
        """Check if a syntax is registered.

        Args:
            name: The syntax name to check

        Returns:
            True if syntax is registered
        """
        return name in self._entries

    def get_priority(self, name: str) -> int | None:
        """Get the priority of a registered syntax.

        Args:
            name: The syntax name

        Returns:
            Priority value or None if not found
        """
        entry = self._entries.get(name)
        return entry.priority if entry else None

    # Methods for future tracks

    def register_validator(self, block_type: BlockType, validator: ValidatorFunc) -> None:
        """Register a validator for a block type.

        Args:
            block_type: The block type to validate
            validator: Function that takes (metadata, content) and returns bool
        """
        self._validators[block_type].append(validator)

    def validate_block(
        self, block_type: BlockType, metadata: BaseModel, content: BaseModel
    ) -> tuple[bool, list[str]]:
        """Validate a block using registered validators.

        Args:
            block_type: The block type
            metadata: Block metadata
            content: Block content

        Returns:
            Tuple of (is_valid, error_messages)
        """
        validators = self._validators.get(block_type, [])
        errors: list[str] = []

        for validator in validators:
            try:
                if not validator(metadata, content):
                    errors.append(f"Validation failed for {block_type}")
            except Exception as e:
                errors.append(f"Validator error: {e}")

        return len(errors) == 0, errors

    def unregister_syntax(self, name: str) -> None:
        """Unregister a syntax.

        Args:
            name: The syntax name to unregister

        Raises:
            KeyError: If syntax not found
        """
        if name not in self._entries:
            raise KeyError(f"Syntax '{name}' not found")

        # Remove from entries
        entry = self._entries.pop(name)

        # Remove from block type mappings
        for block_type in entry.block_types:
            if block_type in self._block_types:
                self._block_types[block_type].remove(name)
                if not self._block_types[block_type]:
                    del self._block_types[block_type]

    def clear(self) -> None:
        """Clear all registered syntaxes."""
        self._entries.clear()
        self._block_types.clear()
        self._validators.clear()
        self._priority_sorted = False
