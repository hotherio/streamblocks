"""Type-specific registry for StreamBlocks."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from hother.streamblocks.core._logger import StdlibLoggerAdapter
from hother.streamblocks.prompts.builder import extract_content_class, extract_schema
from hother.streamblocks.prompts.inspector import inspect_content_format, parse_block_docstring
from hother.streamblocks.prompts.manager import TemplateManager
from hother.streamblocks.syntaxes.models import get_syntax_instance

if TYPE_CHECKING:
    from pathlib import Path

    from hother.streamblocks.core._logger import Logger
    from hother.streamblocks.core.models import Block, ExtractedBlock
    from hother.streamblocks.syntaxes.base import BaseSyntax
    from hother.streamblocks.syntaxes.models import Syntax


type BlockType = str
type ValidatorFunc = Callable[[ExtractedBlock[Any, Any]], bool]


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
        syntax: Syntax | BaseSyntax | None = None,
        logger: Logger | None = None,
        blocks: dict[str, type[Block[Any, Any]]] | None = None,
    ) -> None:
        """Initialize registry with a single syntax instance.

        Args:
            syntax: The syntax instance for this registry. If None, uses global
                   default or system default (DELIMITER_FRONTMATTER)
            logger: Optional logger (any object with debug/info/warning/error/exception methods).
                   Defaults to stdlib logging.getLogger(__name__)
            blocks: Optional dict of block_type -> block_class for bulk registration
        """
        from hother.streamblocks.syntaxes.utils import resolve_syntax

        resolved_syntax = resolve_syntax(syntax)
        self._syntax = get_syntax_instance(syntax=resolved_syntax)
        self._block_classes: dict[BlockType, type[Block[Any, Any]]] = {}
        self._validators: dict[BlockType, list[ValidatorFunc]] = {}
        self._descriptions: dict[BlockType, str] = {}
        self._template_manager = TemplateManager()
        self.logger = logger or StdlibLoggerAdapter(logging.getLogger(__name__))

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
        block_class: type[Block[Any, Any]],
        validators: list[ValidatorFunc] | None = None,
        description: str | None = None,
    ) -> None:
        """Register a block class for a block type.

        Args:
            name: Block type name (e.g., "files_operations", "patch")
            block_class: Block class inheriting from Block[M, C]
            validators: Optional list of validator functions for this block type
            description: Optional custom description for LLM prompts
        """
        self._block_classes[name] = block_class

        self.logger.debug(
            "block_type_registered",
            block_type=name,
            block_class=block_class.__name__,
            has_validators=validators is not None and len(validators) > 0,
        )

        # Add validators if provided
        if validators:
            for validator in validators:
                self.add_validator(name, validator)

        # Store description if provided
        if description:
            self._descriptions[name] = description

    def get_block_class(self, block_type: str) -> type[Block[Any, Any]] | None:
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

        self.logger.debug(
            "validator_added",
            block_type=block_type,
            validator_name=validator.__name__,
            total_validators=len(self._validators[block_type]),
        )

    def validate_block(
        self,
        block: ExtractedBlock[Any, Any],
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

    def register_template(self, version: str, template: str | Path, mode: str = "both") -> None:
        """Register a custom template version for prompt generation.

        This allows A/B testing of different prompt formats.

        Args:
            version: Template version identifier (e.g., "v2", "concise")
            template: Template string or path to template file
            mode: Which mode to register for: "registry", "single", or "both"

        Example:
            >>> registry.register_template("concise", "Blocks: {{ blocks|length }}")
            >>> prompt = registry.to_prompt(template_version="concise")
        """
        self._template_manager.register_template(version, template, mode)

    def to_prompt(
        self,
        include_examples: bool = True,
        template_version: str = "default",
    ) -> str:
        """Generate LLM instruction prompt from registry.

        Creates a comprehensive prompt explaining all registered block types,
        their schemas, and examples. Examples are automatically pulled from
        each Block's model_config.

        Args:
            include_examples: Whether to include examples from block model_config
            template_version: Template version for A/B testing

        Returns:
            String prompt ready to be used in LLM messages

        Example:
            >>> registry = Registry(syntax=DelimiterPreambleSyntax())
            >>> registry.register("files", FileOperations)
            >>> prompt = registry.to_prompt()
            >>> # Use in your LLM system
            >>> messages = [{"role": "system", "content": prompt}]
        """
        context = self._build_context(include_examples)
        return self._template_manager.render(context, template_version, mode="registry")

    def serialize_block(self, block: Block[Any, Any]) -> str:
        """Serialize a block using the registry's syntax.

        Args:
            block: Block instance to serialize

        Returns:
            String representation in this registry's syntax format

        Example:
            >>> block = FileOperations.from_dict({...})
            >>> text = registry.serialize_block(block)
            >>> print(text)
            !!file01:files_operations
            src/main.py:C
            !!end
        """
        return self._syntax.serialize_block(block)

    def _build_context(self, include_examples: bool) -> dict[str, Any]:
        """Build template context for prompt generation.

        Args:
            include_examples: Whether to include examples

        Returns:
            Context dictionary for Jinja2 templates
        """
        context: dict[str, Any] = {
            "syntax_name": self._syntax.__class__.__name__,
            "syntax_format": self._syntax.describe_format(),
            "blocks": [],
        }

        for block_type, block_class in self._block_classes.items():
            # Parse block docstring for description and usage
            block_desc, block_usage = parse_block_docstring(block_class)

            # Extract content class and inspect format
            content_class = extract_content_class(block_class)
            content_format = inspect_content_format(content_class) if content_class else None

            block_info: dict[str, Any] = {
                "name": block_type,
                "description": block_desc or self._descriptions.get(block_type, ""),
                "usage": block_usage,
                "content_format": content_format,
                "metadata_schema": extract_schema(block_class, "metadata"),
                "content_schema": extract_schema(block_class, "content"),
                "examples": [],
                "validator_count": len(self._validators.get(block_type, [])),
            }

            # Get examples from __examples__ and serialize them
            if include_examples:
                examples = block_class.get_examples()
                for example in examples:
                    serialized = self._syntax.serialize_block(example)
                    block_info["examples"].append(serialized)

            context["blocks"].append(block_info)

        return context
