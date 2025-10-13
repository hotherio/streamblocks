"""Core models for StreamBlocks."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any, ClassVar, Generic

import yaml
from pydantic import BaseModel, Field

from hother.streamblocks.core.types import BaseContent, BaseMetadata, BlockState, TContent, TMetadata

if TYPE_CHECKING:
    from typing import Self

    from hother.streamblocks.syntaxes.base import BaseSyntax
    from hother.streamblocks.syntaxes.models import Syntax


def extract_block_types(block_class: type[Any]) -> tuple[type[BaseMetadata], type[BaseContent]]:
    """Extract metadata and content type parameters from a Block class.

    For classes inheriting from Block[M, C], Pydantic resolves the concrete
    types and stores them in the field annotations. We simply extract them
    from the model_fields.

    Args:
        block_class: The block class to extract types from

    Returns:
        Tuple of (metadata_class, content_class)
    """
    # Extract from Pydantic field annotations
    if hasattr(block_class, "model_fields"):
        metadata_field = block_class.model_fields.get("metadata")
        content_field = block_class.model_fields.get("content")

        if metadata_field and content_field:
            return (metadata_field.annotation, content_field.annotation)

    # Fallback to base classes
    return (BaseMetadata, BaseContent)


class BlockCandidate:
    """Tracks a potential block being accumulated."""

    def __init__(self, syntax: BaseSyntax, start_line: int) -> None:
        """Initialize a new block candidate.

        Args:
            syntax: The syntax handler for this block
            start_line: Line number where the block started
        """
        self.syntax = syntax
        self.start_line = start_line
        self.lines: list[str] = []
        self.state = BlockState.HEADER_DETECTED
        self.metadata_lines: list[str] = []
        self.content_lines: list[str] = []
        self.current_section: str = "header"  # "header", "metadata", "content"

    def add_line(self, line: str) -> None:
        """Add a line to the candidate."""
        self.lines.append(line)

    @property
    def raw_text(self) -> str:
        """Get the raw text of all accumulated lines."""
        return "\n".join(self.lines)

    def compute_hash(self) -> str:
        """Compute hash of first 64 chars for ID."""
        text_slice = self.raw_text[:64]
        return hashlib.sha256(text_slice.encode()).hexdigest()[:8]


class Block(BaseModel, Generic[TMetadata, TContent]):
    """User-facing base class for defining block types.

    This minimal class contains only the essential fields (metadata and content).
    Users inherit from this to define their block types.

    Usage:
        class YesNo(Block[YesNoMetadata, YesNoContent]):
            pass

        # Access fields
        block: Block[YesNoMetadata, YesNoContent]
        block.metadata.prompt  # Type-safe access to metadata fields
        block.content.response  # Type-safe access to content fields
    """

    metadata: TMetadata = Field(..., description="Parsed block metadata")
    content: TContent = Field(..., description="Parsed block content")

    # Class-level storage for dynamically added examples
    _examples_storage: ClassVar[dict[type, list[Any]]] = {}

    # Creation methods
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Create block from dictionary.

        Uses Pydantic's model_validate to construct and validate the block.

        Args:
            data: Dictionary with 'metadata' and 'content' keys

        Returns:
            Validated block instance

        Example:
            >>> FileOperations.from_dict({
            ...     "metadata": {"id": "ex1", "block_type": "files_operations"},
            ...     "content": {"operations": [{"action": "create", "path": "main.py"}]}
            ... })
        """
        return cls.model_validate(data)

    @classmethod
    def from_json(cls, json_str: str) -> Self:
        """Create block from JSON string.

        Uses Pydantic's model_validate_json for efficient JSON parsing.

        Args:
            json_str: JSON string representing the block

        Returns:
            Validated block instance

        Example:
            >>> json_data = '{"metadata": {"id": "ex1", "block_type": "files_operations"}, ...}'
            >>> FileOperations.from_json(json_data)
        """
        return cls.model_validate_json(json_str)

    @classmethod
    def from_yaml(cls, yaml_str: str) -> Self:
        """Create block from YAML string.

        Parses YAML and validates using Pydantic.

        Args:
            yaml_str: YAML string representing the block

        Returns:
            Validated block instance

        Example:
            >>> yaml_data = '''
            ... metadata:
            ...   id: ex1
            ...   block_type: files_operations
            ... content:
            ...   operations:
            ...     - action: create
            ...       path: main.py
            ... '''
            >>> FileOperations.from_yaml(yaml_data)
        """
        data = yaml.safe_load(yaml_str)
        return cls.model_validate(data)

    @classmethod
    def from_syntax(cls, text: str, syntax: Syntax | BaseSyntax | None = None) -> Self:
        """Create block by parsing text with a syntax.

        This method uses a syntax parser to extract metadata and content
        from formatted text (e.g., delimiter blocks, markdown blocks).

        Args:
            text: Text to parse in the syntax's format
            syntax: Syntax to use. If None, uses global default or system default
                   (DELIMITER_FRONTMATTER)

        Returns:
            Validated block instance

        Raises:
            ValueError: If parsing fails

        Example:
            >>> text = '''
            ... !!start
            ... ---
            ... id: ex1
            ... block_type: files_operations
            ... ---
            ... src/main.py:C
            ... !!end
            ... '''
            >>> FileOperations.from_syntax(text)  # Uses default syntax
        """
        from hother.streamblocks.syntaxes.models import get_syntax_instance
        from hother.streamblocks.syntaxes.utils import resolve_syntax

        # Resolve syntax with priority: provided > global > system default
        resolved_syntax = resolve_syntax(syntax)
        syntax_instance = get_syntax_instance(syntax=resolved_syntax)

        # Create candidate and parse
        lines = text.strip().split("\n")
        candidate = BlockCandidate(syntax=syntax_instance, start_line=0)
        for line in lines:
            candidate.add_line(line)

        result = syntax_instance.parse_block(candidate, block_class=cls)

        if not result.success:
            msg = f"Failed to parse block: {result.error}"
            raise ValueError(msg)

        return cls(metadata=result.metadata, content=result.content)

    @classmethod
    def add_example(cls, example: Self | dict[str, Any]) -> None:
        """Add a single example to the block class.

        Examples can be added as either a Block instance or a dictionary.
        Dictionaries are validated and converted to Block instances.

        Args:
            example: Block instance or dictionary with 'metadata' and 'content' keys

        Raises:
            ValidationError: If the example dict fails Pydantic validation

        Example:
            >>> # Add as dict
            >>> FileOperations.add_example({
            ...     "metadata": {"id": "ex1", "block_type": "files_operations"},
            ...     "content": {"operations": [{"action": "create", "path": "main.py"}]}
            ... })
            >>> # Add as instance
            >>> example = FileOperations(...)
            >>> FileOperations.add_example(example)
        """
        # Initialize storage for this class if not exists
        if cls not in cls._examples_storage:
            cls._examples_storage[cls] = []

        # Convert dict to instance if needed
        if isinstance(example, dict):
            # Use the same auto-generation logic as get_examples
            import json

            if "content" in example and "raw_content" not in example["content"]:
                content_data = dict(example["content"])

                # Special case: FileOperations with operations list
                if "operations" in content_data:
                    action_map = {"create": "C", "edit": "E", "delete": "D"}
                    lines = []
                    for op in content_data["operations"]:
                        action_code = action_map.get(op["action"], "C")
                        lines.append(f"{op['path']}:{action_code}")
                    raw_content = "\n".join(lines)
                else:
                    # Detect format from metadata if available
                    format_type = "json"  # Default to JSON
                    if "metadata" in example and "format" in example["metadata"]:
                        format_type = example["metadata"]["format"]

                    # Generate raw_content by serializing content fields
                    serializable_content = {k: v for k, v in content_data.items() if k not in ("raw_content",)}

                    if format_type == "yaml":
                        import yaml as yaml_lib

                        raw_content = yaml_lib.dump(
                            serializable_content, default_flow_style=False, sort_keys=False
                        ).strip()
                    else:  # json
                        raw_content = json.dumps(serializable_content, ensure_ascii=False)

                # Add raw_content to the example data
                example["content"]["raw_content"] = raw_content

            # Validate and convert to instance (this will raise ValidationError if invalid)
            example_instance = cls.model_validate(example)
        else:
            example_instance = example

        # Add to storage
        cls._examples_storage[cls].append(example_instance)

    @classmethod
    def add_examples(cls, examples: list[Self | dict[str, Any]]) -> None:
        """Add multiple examples to the block class.

        Args:
            examples: List of Block instances or dictionaries

        Raises:
            ValidationError: If any example dict fails Pydantic validation

        Example:
            >>> FileOperations.add_examples([
            ...     {"metadata": {...}, "content": {...}},
            ...     {"metadata": {...}, "content": {...}},
            ... ])
        """
        for example in examples:
            cls.add_example(example)

    @classmethod
    def add_example_from_syntax(cls, text: str, syntax: Syntax | BaseSyntax | None = None) -> None:
        """Parse and add an example from syntax-formatted text.

        This method parses a block from text using the specified syntax,
        then adds it as an example. This is useful for defining examples
        in their actual syntax format rather than as dictionaries.

        Args:
            text: Text in the specified syntax format
            syntax: Syntax to use. If None, uses global default or system default
                   (DELIMITER_FRONTMATTER)

        Raises:
            ValueError: If parsing fails

        Example:
            >>> text = '''
            ... !!start
            ... ---
            ... id: ex1
            ... block_type: files_operations
            ... ---
            ... src/main.py:C
            ... src/utils.py:C
            ... !!end
            ... '''
            >>> FileOperations.add_example_from_syntax(text)  # Uses default syntax
        """
        # Use existing from_syntax method to parse (uses resolver internally)
        example_instance = cls.from_syntax(text, syntax)

        # Add the parsed instance
        cls.add_example(example_instance)

    @classmethod
    def clear_examples(cls) -> None:
        """Clear all dynamically added examples for this block class.

        This does NOT clear examples defined in __examples__ class attribute.
        Only clears examples added via add_example() methods.

        Example:
            >>> FileOperations.clear_examples()
            >>> len(FileOperations.get_examples())  # May still have __examples__
        """
        if cls in cls._examples_storage:
            cls._examples_storage[cls] = []

    @classmethod
    def get_examples(cls) -> list[Self]:
        """Get all examples for this block class.

        Returns both static examples (from __examples__ attribute) and
        dynamic examples (added via add_example methods). Examples are
        automatically validated and converted to Block instances.

        If `raw_content` is missing from content in __examples__, it will be
        automatically generated:
        - For JSON/YAML formats: Serializes content fields to JSON or YAML
        - For FileOperations: Converts operations list to file format (path:action)
        - For other custom formats: Uses the content fields as-is

        Returns:
            List of Block instances (static __examples__ + dynamic examples)

        Example:
            >>> class MyBlock(Block[MyMetadata, MyContent]):
            ...     __examples__ = [{"metadata": {...}, "content": {...}}]
            >>> MyBlock.add_example({"metadata": {...}, "content": {...}})
            >>> examples = MyBlock.get_examples()
            >>> len(examples)  # Returns 2 (1 static + 1 dynamic)
            2
        """
        import json

        # Get examples from __examples__ class attribute (static)
        examples_data = getattr(cls, "__examples__", [])

        # Convert example dicts to Block instances
        examples: list[Self] = []
        for example_data in examples_data:
            try:
                # Auto-generate raw_content if missing
                if "content" in example_data and "raw_content" not in example_data["content"]:
                    content_data = dict(example_data["content"])

                    # Special case: FileOperations with operations list
                    if "operations" in content_data:
                        action_map = {"create": "C", "edit": "E", "delete": "D"}
                        lines = []
                        for op in content_data["operations"]:
                            action_code = action_map.get(op["action"], "C")
                            lines.append(f"{op['path']}:{action_code}")
                        raw_content = "\n".join(lines)
                    else:
                        # Detect format from metadata if available
                        format_type = "json"  # Default to JSON
                        if "metadata" in example_data and "format" in example_data["metadata"]:
                            format_type = example_data["metadata"]["format"]

                        # Generate raw_content by serializing content fields (excluding raw_content itself)
                        serializable_content = {k: v for k, v in content_data.items() if k not in ("raw_content",)}

                        if format_type == "yaml":
                            import yaml as yaml_lib

                            raw_content = yaml_lib.dump(
                                serializable_content, default_flow_style=False, sort_keys=False
                            ).strip()
                        else:  # json
                            raw_content = json.dumps(serializable_content, ensure_ascii=False)

                    # Add raw_content to the example data
                    example_data["content"]["raw_content"] = raw_content

                example = cls.model_validate(example_data)
                examples.append(example)
            except Exception:
                # Skip invalid examples
                continue

        # Add dynamic examples from _examples_storage
        if cls in cls._examples_storage:
            examples.extend(cls._examples_storage[cls])

        return examples

    @classmethod
    def to_prompt(
        cls,
        syntax: Syntax | BaseSyntax | None = None,
        include_examples: bool = True,
        template_version: str = "default",
    ) -> str:
        """Generate LLM instruction prompt for this block type.

        This method creates a prompt explaining how to output this block type
        using the specified syntax. It automatically includes the syntax format,
        schema information, and examples.

        If the block class has a `__prompt__` class attribute, that custom prompt
        string will be returned directly, bypassing template generation.

        Args:
            syntax: Syntax to use. If None, uses global default or system default
                   (DELIMITER_FRONTMATTER)
            include_examples: Whether to include examples from __examples__
            template_version: Template version for A/B testing

        Returns:
            String prompt for this single block type

        Example:
            >>> from hother.streamblocks.blocks import FileOperations
            >>> prompt = FileOperations.to_prompt()  # Uses default syntax
            >>> print(prompt)
            # FileOperations Block
            ...

            >>> # With custom prompt
            >>> class MyBlock(Block[MyMetadata, MyContent]):
            ...     __prompt__ = '''
            ...     # My Custom Block
            ...     Use this block for custom operations.
            ...     '''
            >>> prompt = MyBlock.to_prompt()
        """
        # Check for custom prompt first
        if hasattr(cls, "__prompt__"):
            custom_prompt = cls.__prompt__
            if isinstance(custom_prompt, str):
                return custom_prompt.strip()

        # Use template generation
        from hother.streamblocks.prompts import generate_block_prompt
        from hother.streamblocks.syntaxes.models import get_syntax_instance
        from hother.streamblocks.syntaxes.utils import resolve_syntax

        # Resolve syntax with priority: provided > global > system default
        resolved_syntax = resolve_syntax(syntax)
        syntax_instance = get_syntax_instance(syntax=resolved_syntax)

        return generate_block_prompt(
            block_class=cls,
            syntax=syntax_instance,
            include_examples=include_examples,
            template_version=template_version,
        )


class ExtractedBlock[TMetadata: BaseMetadata, TContent: BaseContent](Block[TMetadata, TContent]):
    """Full runtime representation of an extracted block.

    This class extends the minimal Block with extraction metadata like
    line numbers, syntax name, and hash ID. The processor creates instances
    of this class when blocks are successfully extracted.

    The metadata and content fields are typed generics, allowing type-safe
    access to block-specific fields.
    """

    syntax_name: str = Field(..., description="Name of the syntax that extracted this block")
    raw_text: str = Field(..., description="Original raw text of the block")
    line_start: int = Field(..., description="Starting line number")
    line_end: int = Field(..., description="Ending line number")
    hash_id: str = Field(..., description="Hash-based ID for the block")
