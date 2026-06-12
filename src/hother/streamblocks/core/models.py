"""Core models for StreamBlocks."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Self, cast

import yaml
from pydantic import BaseModel, Field

from hother.streamblocks.core.constants import LIMITS
from hother.streamblocks.core.types import BaseContent, BaseMetadata, BlockState, SectionType

if TYPE_CHECKING:
    from hother.streamblocks.syntaxes.base import BaseSyntax

# YAML frontmatter delimiters for markdown examples files
_FRONTMATTER_FENCE = "---"
# A valid frontmatter document splits into [pre, frontmatter, body] on the fence
_FRONTMATTER_PART_COUNT = 3


def extract_block_types(block_class: type[Any]) -> tuple[type[BaseMetadata], type[BaseContent]]:
    """Extract metadata and content type parameters from a Block class.

    For classes inheriting from Block[M, C], Pydantic resolves the concrete
    types and stores them in the field annotations during class definition.
    This function extracts those resolved types from model_fields.

    Args:
        block_class: The block class to extract types from

    Returns:
        Tuple of (metadata_class, content_class)
    """
    # Extract type parameters from Pydantic field annotations
    # Pydantic resolves Block[M, C] generics during class definition
    if issubclass(block_class, BaseModel):
        metadata_field = block_class.model_fields.get("metadata")
        content_field = block_class.model_fields.get("content")

        if (
            metadata_field
            and content_field
            and metadata_field.annotation is not None
            and content_field.annotation is not None
        ):
            return (metadata_field.annotation, content_field.annotation)

    # Fallback to base classes
    return (BaseMetadata, BaseContent)


class BlockCandidate:
    """Tracks a potential block being accumulated."""

    __slots__ = (
        "content_lines",
        "content_validation_error",
        "content_validation_passed",
        "current_section",
        "lines",
        "metadata_lines",
        "metadata_validation_error",
        "metadata_validation_passed",
        "parsed_content",
        "parsed_metadata",
        "start_line",
        "state",
        "syntax",
    )

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
        self.current_section: SectionType = SectionType.HEADER

        # Cache fields for early parsing results
        self.parsed_metadata: dict[str, Any] | None = None
        self.parsed_content: dict[str, Any] | None = None

        # Validation state for section end events
        self.metadata_validation_passed: bool = True
        self.metadata_validation_error: str | None = None
        self.content_validation_passed: bool = True
        self.content_validation_error: str | None = None

    def add_line(self, line: str) -> None:
        """Add a line to the candidate."""
        self.lines.append(line)

    def transition_to_metadata(self) -> None:
        """Transition from header to metadata section.

        This method encapsulates the section state transition logic,
        making the state change explicit and centralized.
        """
        self.current_section = SectionType.METADATA

    def transition_to_content(self) -> None:
        """Transition from metadata/header to content section.

        This method encapsulates the section state transition logic,
        making the state change explicit and centralized.
        """
        self.current_section = SectionType.CONTENT

    def cache_metadata_validation(self, passed: bool, error: str | None) -> None:
        """Cache metadata validation result.

        This method encapsulates validation result storage, providing
        a clear interface for the state machine to cache validation state.

        Args:
            passed: Whether metadata validation passed
            error: Error message if validation failed, None otherwise
        """
        self.metadata_validation_passed = passed
        self.metadata_validation_error = error

    def cache_content_validation(self, passed: bool, error: str | None) -> None:
        """Cache content validation result.

        This method encapsulates validation result storage, providing
        a clear interface for the state machine to cache validation state.

        Args:
            passed: Whether content validation passed
            error: Error message if validation failed, None otherwise
        """
        self.content_validation_passed = passed
        self.content_validation_error = error

    @property
    def raw_text(self) -> str:
        """Get the raw text of all accumulated lines."""
        return "\n".join(self.lines)

    def compute_hash(self) -> str:
        """Compute hash of first N chars for ID (N defined in constants)."""
        text_slice = self.raw_text[: LIMITS.HASH_PREFIX_LENGTH]
        return hashlib.sha256(text_slice.encode()).hexdigest()[:8]

    def __repr__(self) -> str:
        """Return a developer-friendly string representation."""
        return (
            f"BlockCandidate(syntax={type(self.syntax).__name__}, "
            f"start_line={self.start_line}, state={self.state.value}, "
            f"lines={len(self.lines)}, section={self.current_section!r})"
        )


class Block[TMetadata: BaseMetadata, TContent: BaseContent](BaseModel):
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

    # Declared examples for this block type. Either a list of
    # {"metadata": {...}, "content": {...}} dicts, or a path (Path or str) to a
    # markdown file with YAML frontmatter that names the syntax. Used by prompt
    # generation.
    __examples__: ClassVar[list[dict[str, Any]] | Path | str] = []

    # Examples added at runtime via add_example(), keyed by concrete class so
    # subclasses do not share storage.
    _dynamic_examples: ClassVar[dict[type, list[Any]]] = {}
    # Cache of file-loaded examples keyed by (class, resolved_path, mtime).
    _examples_file_cache: ClassVar[dict[tuple[type, str, float], list[Any]]] = {}

    @classmethod
    def add_example(cls, example: Self | dict[str, Any]) -> None:
        """Add a single example for this block type.

        Args:
            example: A block instance, or a dict with ``metadata`` and
                ``content`` keys. Missing ``raw_content`` is auto-filled.
        """
        instance = cls._example_from_dict(example) if isinstance(example, dict) else example
        cls._dynamic_examples.setdefault(cls, []).append(instance)

    @classmethod
    def add_examples(cls, examples: list[Self | dict[str, Any]]) -> None:
        """Add multiple examples for this block type."""
        for example in examples:
            cls.add_example(example)

    @classmethod
    def clear_examples(cls) -> None:
        """Clear examples added via add_example().

        Does not affect examples declared in the ``__examples__`` attribute.
        """
        cls._dynamic_examples[cls] = []

    @classmethod
    def get_examples(cls) -> list[Self]:
        """Return all examples (declared + dynamically added) as instances.

        Declared examples come from ``__examples__`` (inline dicts or a markdown
        file). Dynamically added examples come from :meth:`add_example`.
        """
        declared = cls.__examples__
        if isinstance(declared, (str, Path)):
            examples = cls._load_examples_from_file(declared)
        else:
            examples = [cls._example_from_dict(item) for item in declared]
        examples.extend(cls._dynamic_examples.get(cls, []))
        return examples

    @classmethod
    def _example_from_dict(cls, data: dict[str, Any]) -> Self:
        """Validate an example dict into an instance, auto-filling raw_content."""
        return cls.model_validate(cls._ensure_raw_content(data))

    @classmethod
    def _ensure_raw_content(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Fill a missing content ``raw_content`` by serializing content fields.

        Honors an explicit ``raw_content`` when present. The serialization
        format follows the block's declared content format
        (``__content_format__`` set by ``@parse_as_json`` / ``@parse_as_yaml``),
        defaulting to JSON. Block types with bespoke content formats should
        provide ``raw_content`` explicitly in their examples.
        """
        content_value = data.get("content")
        if not isinstance(content_value, dict) or "raw_content" in content_value:
            return data
        content = cast("dict[str, Any]", content_value)
        fields = {key: value for key, value in content.items() if key != "raw_content"}
        _, content_class = extract_block_types(cls)
        if content_class.__content_format__ == "yaml":
            raw_content = yaml.dump(fields, default_flow_style=False, sort_keys=False).strip()
        else:
            raw_content = json.dumps(fields, ensure_ascii=False)
        return {**data, "content": {**content, "raw_content": raw_content}}

    @classmethod
    def _load_examples_from_file(cls, path: Path | str) -> list[Self]:
        """Load and cache examples from a markdown file with YAML frontmatter."""
        file_path = Path(path).resolve()
        if not file_path.is_file():
            msg = f"Examples file not found: {file_path}"
            raise FileNotFoundError(msg)

        mtime = file_path.stat().st_mtime
        cache_key = (cls, str(file_path), mtime)
        cached = cls._examples_file_cache.get(cache_key)
        if cached is not None:
            return list(cached)

        content = file_path.read_text(encoding="utf-8")
        syntax, blocks_content = cls._parse_examples_frontmatter(content, file_path)
        examples = cls._extract_blocks_from_content(blocks_content, syntax)
        cls._examples_file_cache[cache_key] = examples
        return list(examples)

    @classmethod
    def _parse_examples_frontmatter(cls, content: str, file_path: Path) -> tuple[BaseSyntax, str]:
        """Split a markdown examples file into (syntax instance, blocks text)."""
        from hother.streamblocks.syntaxes.factory import get_syntax_instance
        from hother.streamblocks.syntaxes.models import Syntax

        if not content.lstrip().startswith(_FRONTMATTER_FENCE):
            msg = f"Examples file must start with YAML frontmatter: {file_path}"
            raise ValueError(msg)

        parts = content.split(_FRONTMATTER_FENCE, 2)
        if len(parts) < _FRONTMATTER_PART_COUNT:
            msg = f"Invalid frontmatter in examples file: {file_path}"
            raise ValueError(msg)

        parsed = yaml.safe_load(parts[1].strip())
        if not isinstance(parsed, dict):
            msg = f"Frontmatter must be a YAML mapping: {file_path}"
            raise TypeError(msg)

        frontmatter = cast("dict[str, Any]", parsed)
        syntax_name = frontmatter.get("syntax")
        if not isinstance(syntax_name, str):
            msg = f"Frontmatter must name a string 'syntax' field: {file_path}"
            raise TypeError(msg)

        try:
            syntax = get_syntax_instance(Syntax[syntax_name])
        except KeyError as error:
            valid = ", ".join(member.name for member in Syntax)
            msg = f"Unknown syntax '{syntax_name}' in {file_path}. Valid options: {valid}"
            raise ValueError(msg) from error

        return syntax, parts[2].strip()

    @classmethod
    def _extract_blocks_from_content(cls, content: str, syntax: BaseSyntax) -> list[Self]:
        """Parse all blocks in a text body using the given syntax."""
        examples: list[Self] = []
        candidate: BlockCandidate | None = None
        for line in content.split("\n"):
            if candidate is None:
                if syntax.detect_line(line, None).is_opening:
                    candidate = BlockCandidate(syntax=syntax, start_line=0)
                    candidate.add_line(line)
                continue
            candidate.add_line(line)
            if syntax.detect_line(line, candidate).is_closing:
                result = syntax.parse_block(candidate, block_class=cls)
                if not result.success or result.metadata is None or result.content is None:
                    msg = f"Failed to parse example block: {result.error or 'incomplete block'}"
                    raise ValueError(msg)
                examples.append(cls.model_validate({"metadata": result.metadata, "content": result.content}))
                candidate = None
        return examples


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
