"""Delimiter-based syntax implementations."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

import yaml

from hother.streamblocks.core.models import extract_block_types
from hother.streamblocks.core.types import BaseContent, BaseMetadata, DetectionResult, ParseResult, SectionType
from hother.streamblocks.grammar.nodes import (
    CharSet,
    Choice,
    Literal,
    Node,
    Ref,
    SharedLines,
    line_not_starting_with,
    one_or_more,
    optional,
    seq,
)
from hother.streamblocks.grammar.spec import BlockSpec, GrammarError, MetadataField, SyntaxGrammar
from hother.streamblocks.grammar.values import IDENTIFIER, IDENTIFIER_RULE, WORD, WORD_RULE, quoted_string, scalar
from hother.streamblocks.syntaxes.base import BaseSyntax, YAMLFrontmatterMixin

if TYPE_CHECKING:
    from collections.abc import Sequence

    from hother.streamblocks.core.models import Block, BlockCandidate, ExtractedBlock

# Positional preamble parameters are metadata fields named param_0, param_1, ...
_PARAM_FIELD_PATTERN = re.compile(r"^param_(\d+)$")
_WORD_PATTERN = re.compile(r"^\w+$")

# Characters a double-quoted YAML string cannot hold without escaping
_YAML_STRING_EXCLUDED = "\\\n"

# Minimum lines required for a block (header + closing delimiter)
_MIN_BLOCK_LINES = 2


def _remainder_after(text: str, marker: str) -> str | None:
    """Return the text following ``marker`` when ``text`` starts with it, else None.

    This is the lenient-close policy: models often keep writing right after a
    closing marker without a newline (``!!endYour answer``). Any non-blank text
    after the marker counts, so a content line that itself starts with the
    marker is read as a close; disable ``lenient_close`` on the syntax if block
    content can legitimately start with the closing marker.
    """
    if not text.startswith(marker):
        return None
    return text[len(marker) :].strip() or None


@runtime_checkable
class ContentParser(Protocol):
    """Protocol for content classes with a parse method."""

    @classmethod
    def parse(cls, raw_text: str) -> BaseContent:
        """Parse raw text into content."""
        ...


class DelimiterPreambleSyntax(BaseSyntax):
    """Syntax: !! delimiter with inline metadata.

    This syntax uses delimiter markers with inline metadata in the opening line.
    Metadata is extracted from the delimiter preamble, and all lines between
    opening and closing delimiters become the content.

    Format:
        !!<id>:<type>[:param1:param2:...]
        Content lines here
        !!end

    The opening delimiter must include:
        - Block ID (alphanumeric, required)
        - Block type (alphanumeric, required)
        - Additional parameters (optional, colon-separated)

    Additional parameters are stored as param_0, param_1, etc. in metadata.

    Examples:
        >>> # Simple block with just ID and type
        >>> '''
        ... !!patch001:patch
        ... Fix the login bug
        ... !!end
        ... '''
        >>>
        >>> # Block with parameters
        >>> '''
        ... !!file123:operation:create:urgent
        ... Create new config file
        ... !!end
        ... '''
        >>> # Metadata will be: {
        >>> #     "id": "file123",
        >>> #     "block_type": "operation",
        >>> #     "param_0": "create",
        >>> #     "param_1": "urgent"
        >>> # }

    Args:
        delimiter: Opening delimiter string (default: "!!")
        lenient_close: Treat ``!!end`` followed by text on the same line as a
            close, and re-process that text as a new line (default: True)
    """

    def __init__(
        self,
        delimiter: str = "!!",
        *,
        lenient_close: bool = True,
    ) -> None:
        """Initialize delimiter preamble syntax.

        Args:
            delimiter: Delimiter string to use
        """
        self.delimiter = delimiter
        self.lenient_close = lenient_close
        self._end_marker = f"{delimiter}end"
        self._opening_pattern = re.compile(rf"^{re.escape(delimiter)}(\w+):(\w+)(:.+?)?\s*$")
        self._closing_pattern = re.compile(rf"^{re.escape(delimiter)}end\s*$")

    def detect_line(self, line: str, candidate: BlockCandidate | None = None) -> DetectionResult:
        """Detect delimiter-based markers."""
        if candidate is None:
            # Looking for opening
            match = self._opening_pattern.match(line)
            if match:
                block_id, block_type, params = match.groups()
                metadata_dict: dict[str, object] = {
                    "id": block_id,
                    "block_type": block_type,
                }

                if params:
                    param_parts = params[1:].split(":")
                    for i, part in enumerate(param_parts):
                        metadata_dict[f"param_{i}"] = part

                return DetectionResult(
                    is_opening=True,
                    metadata=metadata_dict,  # Inline metadata
                )
        # Check for closing
        elif self._closing_pattern.match(line):
            return DetectionResult(is_closing=True)
        # An opening marker such as "!!endpoint:type" is never a lenient close
        elif self.lenient_close and not self._opening_pattern.match(line):
            remainder = _remainder_after(line, self._end_marker)
            if remainder:
                return DetectionResult(is_closing=True, remainder=remainder)

        return DetectionResult()

    def should_accumulate_metadata(self, candidate: BlockCandidate) -> bool:
        """No separate metadata section for this syntax."""
        return False

    def extract_block_type(self, candidate: BlockCandidate) -> str | None:
        """Extract block_type from opening line."""
        if not candidate.lines:
            return None

        # Parse the opening line to get block_type
        detection = self.detect_line(candidate.lines[0], None)
        if detection.metadata and "block_type" in detection.metadata:
            return str(detection.metadata["block_type"])

        return None

    def parse_block(
        self, candidate: BlockCandidate, block_class: type[Any] | None = None
    ) -> ParseResult[BaseMetadata, BaseContent]:
        """Parse the complete block using the specified block class."""

        # Extract metadata and content classes from block_class
        if block_class is None:
            # Default to base classes
            metadata_class = BaseMetadata
            content_class = BaseContent
        else:
            # Extract from block class using type parameters
            metadata_class, content_class = extract_block_types(block_class)

        # Metadata was already extracted during detection
        detection = self.detect_line(candidate.lines[0], None)

        if not detection.metadata:
            return ParseResult(success=False, error="Missing metadata in preamble")

        # Convert all metadata values to strings for type safety
        # Note: id and block_type are always set by detect_line()
        typed_metadata = {k: str(v) for k, v in detection.metadata.items()}

        # Parse metadata using helper
        metadata = self._safe_parse_metadata(metadata_class, typed_metadata)
        if isinstance(metadata, ParseResult):
            return metadata  # Return error

        # Parse content (skip first and last lines)
        content_text = "\n".join(candidate.lines[1:-1])

        # Parse content using helper
        content = self._safe_parse_content(content_class, content_text)
        if isinstance(content, ParseResult):
            return content  # Return error

        return ParseResult(success=True, metadata=metadata, content=content)

    def validate_block(self, _block: ExtractedBlock[BaseMetadata, BaseContent]) -> bool:
        """Additional validation after parsing."""
        return True

    def parse_metadata_early(self, candidate: BlockCandidate) -> dict[str, Any] | None:
        """Parse metadata from inline preamble.

        For this syntax, metadata is extracted from the opening line
        (e.g., !!id:type:param1:param2).
        """
        if not candidate.lines:
            return None

        detection = self.detect_line(candidate.lines[0], None)
        if detection.metadata:
            # Convert all values to strings for consistency
            return {k: str(v) for k, v in detection.metadata.items()}
        return None

    def parse_content_early(self, candidate: BlockCandidate) -> dict[str, Any] | None:
        """Parse content section early.

        Returns raw content dict with the content text.
        """
        if len(candidate.lines) < _MIN_BLOCK_LINES:
            return None

        # Content is all lines except first (header) and last (closing)
        content_lines = candidate.lines[1:-1] if len(candidate.lines) > _MIN_BLOCK_LINES else candidate.lines[1:]
        raw_content = "\n".join(content_lines)
        return {"raw_content": raw_content}

    def serialize_block(self, block: Block[BaseMetadata, BaseContent]) -> str:
        """Serialize a block to delimiter preamble format.

        Produces the round-trip form of this syntax::

            !!<id>:<type>[:<param_0>:<param_1>...]
            <raw content>
            !!end

        Args:
            block: Block instance to serialize

        Returns:
            The block rendered in delimiter preamble format
        """
        metadata = block.metadata
        opening = f"{self.delimiter}{metadata.id}:{metadata.block_type}"

        # Re-emit positional params (param_0, param_1, ...) if present
        params: list[str] = []
        index = 0
        while hasattr(metadata, f"param_{index}"):
            params.append(str(getattr(metadata, f"param_{index}")))
            index += 1
        if params:
            opening += ":" + ":".join(params)

        return f"{opening}\n{block.content.raw_content}\n{self.delimiter}end"

    def describe_format(self) -> str:
        """Describe the delimiter preamble format for prompts."""
        return (
            "Delimiter Preamble Syntax\n\n"
            "Format:\n"
            f"{self.delimiter}<id>:<type>[:<param1>:<param2>...]\n"
            "content lines\n"
            f"{self.delimiter}end\n\n"
            "Components:\n"
            f"- Opening line: {self.delimiter}<id>:<type> where id is unique and type identifies the block\n"
            "- Optional parameters: additional colon-separated values after type\n"
            "- Content: any text between the opening and closing markers\n"
            f"- Closing line: {self.delimiter}end"
        )

    def grammar_rules(self, blocks: Sequence[BlockSpec]) -> SyntaxGrammar:
        """Grammar rules for delimiter preamble blocks.

        Metadata fields other than positional parameters (``param_0``, ...)
        cannot be written in this syntax, so a block that requires one is
        rejected.
        """
        line = SharedLines(self.delimiter)
        rules: dict[str, Node] = {}
        for block in blocks:
            if not _WORD_PATTERN.match(block.block_type):
                msg = f"Block type {block.block_type!r} cannot be written in a preamble (letters, digits, underscores)"
                raise GrammarError(msg)
            rules[block.block_type] = seq(
                self.delimiter,
                Ref(WORD_RULE),
                f":{block.block_type}",
                *self._param_nodes(block),
                "\n",
                block.content(line),
                f"{self._end_marker}\n",
            )
        text_line = line_not_starting_with(self.delimiter)
        return SyntaxGrammar(text_line=text_line, blocks=rules, shared={**line.rules, WORD_RULE: WORD})

    @staticmethod
    def _param_nodes(block: BlockSpec) -> list[Node]:
        """Positional parameters, in order; other required fields cannot be expressed."""
        params: dict[int, MetadataField] = {}
        for metadata_field in block.fields:
            match = _PARAM_FIELD_PATTERN.match(metadata_field.name)
            if match:
                params[int(match.group(1))] = metadata_field
            elif metadata_field.required:
                msg = (
                    f"Block {block.block_type!r} requires field {metadata_field.name!r}, which a preamble cannot carry"
                )
                raise GrammarError(msg)

        value = one_or_more(CharSet(chars=":\n", negated=True))
        nodes: list[Node] = []
        for index in sorted(params):
            param = seq(":", scalar(params[index], string=value, fallback=value))
            nodes.append(param if params[index].required else optional(param))
        return nodes


class DelimiterFrontmatterSyntax(BaseSyntax, YAMLFrontmatterMixin):
    """Syntax: Delimiter markers with YAML frontmatter.

    This syntax uses simple delimiter markers with YAML frontmatter for metadata.
    The frontmatter section is delimited by --- markers and must be valid YAML.

    Format:
        !!start
        ---
        id: block_001
        block_type: example
        custom_field: value
        ---
        Content lines here
        !!end

    The YAML frontmatter should include:
        - id: Block identifier (required if using BaseMetadata)
        - block_type: Block type (required if using BaseMetadata)
        - Any additional custom fields defined in your metadata class

    Examples:
        >>> # Simple block with minimal metadata
        >>> '''
        ... !!start
        ... ---
        ... id: msg001
        ... block_type: message
        ... ---
        ... Hello, world!
        ... !!end
        ... '''
        >>>
        >>> # Block with nested YAML metadata
        >>> '''
        ... !!start
        ... ---
        ... id: task001
        ... block_type: task
        ... priority: high
        ... tags:
        ...   - urgent
        ...   - backend
        ... ---
        ... Implement user authentication
        ... !!end
        ... '''

    Args:
        start_delimiter: Opening delimiter string (default: "!!start")
        end_delimiter: Closing delimiter string (default: "!!end")
        lenient_close: Treat the closing delimiter followed by text on the same
            line as a close, and re-process that text as a new line (default: True)
    """

    def __init__(
        self,
        start_delimiter: str = "!!start",
        end_delimiter: str = "!!end",
        *,
        lenient_close: bool = True,
    ) -> None:
        """Initialize delimiter frontmatter syntax.

        Args:
            start_delimiter: Starting delimiter
            end_delimiter: Ending delimiter
        """
        self.start_delimiter = start_delimiter
        self.end_delimiter = end_delimiter
        self.lenient_close = lenient_close
        self._frontmatter_pattern = re.compile(r"^---\s*$")

    def detect_line(self, line: str, candidate: BlockCandidate | None = None) -> DetectionResult:
        """Detect delimiter markers and frontmatter boundaries."""
        if candidate is None:
            # Looking for opening
            if line.strip() == self.start_delimiter:
                return DetectionResult(is_opening=True)
        # Inside a block
        elif candidate.current_section == SectionType.HEADER:
            # Should be frontmatter start
            if self._frontmatter_pattern.match(line):
                candidate.transition_to_metadata()
                return DetectionResult(is_metadata_boundary=True)
            # Skip empty lines in header - frontmatter might follow
            if line.strip() == "":
                return DetectionResult()
            # Move directly to content if no frontmatter
            candidate.transition_to_content()
            candidate.content_lines.append(line)
        elif candidate.current_section == SectionType.METADATA:
            if self._frontmatter_pattern.match(line):
                candidate.transition_to_content()
                return DetectionResult(is_metadata_boundary=True)
            candidate.metadata_lines.append(line)
        elif candidate.current_section == SectionType.CONTENT:
            return self._detect_in_content(line, candidate)

        return DetectionResult()

    def _detect_in_content(self, line: str, candidate: BlockCandidate) -> DetectionResult:
        """Detect the closing delimiter in the content section, else accumulate the line."""
        stripped = line.strip()
        if stripped == self.end_delimiter:
            return DetectionResult(is_closing=True)
        remainder = _remainder_after(stripped, self.end_delimiter) if self.lenient_close else None
        if remainder:
            return DetectionResult(is_closing=True, remainder=remainder)
        candidate.content_lines.append(line)
        return DetectionResult()

    def should_accumulate_metadata(self, candidate: BlockCandidate) -> bool:
        """Check if we're still in metadata section."""
        return candidate.current_section in {SectionType.HEADER, SectionType.METADATA}

    def extract_block_type(self, candidate: BlockCandidate) -> str | None:
        """Extract block_type from YAML frontmatter."""
        metadata_dict = self._parse_yaml_metadata(candidate.metadata_lines)
        if metadata_dict and "block_type" in metadata_dict:
            return str(metadata_dict["block_type"])
        return None

    def parse_block(
        self, candidate: BlockCandidate, block_class: type[Any] | None = None
    ) -> ParseResult[BaseMetadata, BaseContent]:
        """Parse the complete block using the specified block class."""

        # Extract metadata and content classes from block_class
        if block_class is None:
            # Default to base classes
            metadata_class = BaseMetadata
            content_class = BaseContent
        else:
            # Extract from block class using type parameters
            metadata_class, content_class = extract_block_types(block_class)

        # Parse metadata from accumulated metadata lines
        metadata_dict, yaml_error = self._parse_yaml_metadata_strict(candidate.metadata_lines)
        if yaml_error:
            return ParseResult(success=False, error=f"YAML parse error: {yaml_error}", exception=yaml_error)

        # Parse metadata using helper
        metadata = self._safe_parse_metadata(metadata_class, metadata_dict)
        if isinstance(metadata, ParseResult):
            return metadata  # Return error

        # Parse content using helper
        content_text = "\n".join(candidate.content_lines)
        content = self._safe_parse_content(content_class, content_text)
        if isinstance(content, ParseResult):
            return content  # Return error

        return ParseResult(success=True, metadata=metadata, content=content)

    def validate_block(self, _block: ExtractedBlock[BaseMetadata, BaseContent]) -> bool:
        """Additional validation after parsing."""
        return True

    def parse_metadata_early(self, candidate: BlockCandidate) -> dict[str, Any] | None:
        """Parse YAML metadata section early.

        Returns parsed YAML frontmatter as a dict.
        """
        return self._parse_yaml_metadata(candidate.metadata_lines)

    def parse_content_early(self, candidate: BlockCandidate) -> dict[str, Any] | None:
        """Parse content section early.

        Returns raw content dict with the content text.
        """
        raw_content = "\n".join(candidate.content_lines)
        return {"raw_content": raw_content}

    def serialize_block(self, block: Block[BaseMetadata, BaseContent]) -> str:
        """Serialize a block to delimiter frontmatter format.

        Produces the round-trip form of this syntax::

            !!start
            ---
            <yaml metadata>
            ---
            <raw content>
            !!end

        Args:
            block: Block instance to serialize

        Returns:
            The block rendered in delimiter frontmatter format
        """
        metadata_yaml = yaml.dump(block.metadata.model_dump(), default_flow_style=False, sort_keys=False)
        return f"{self.start_delimiter}\n---\n{metadata_yaml}---\n{block.content.raw_content}\n{self.end_delimiter}"

    def describe_format(self) -> str:
        """Describe the delimiter frontmatter format for prompts."""
        return (
            "Delimiter Frontmatter Syntax\n\n"
            "Format:\n"
            f"{self.start_delimiter}\n"
            "---\n"
            "key: value\n"
            "---\n"
            "content lines\n"
            f"{self.end_delimiter}\n\n"
            "Components:\n"
            f"- Opening marker: {self.start_delimiter}\n"
            "- Metadata section: YAML frontmatter between --- delimiters\n"
            "- Content: any text after the metadata section\n"
            f"- Closing marker: {self.end_delimiter}"
        )

    def grammar_rules(self, blocks: Sequence[BlockSpec]) -> SyntaxGrammar:
        """Grammar rules for delimiter frontmatter blocks.

        The frontmatter lists ``id`` and ``block_type`` first, then the block's
        metadata fields in declaration order. String values are double-quoted.
        """
        line = SharedLines(self.end_delimiter, self.start_delimiter)
        rules: dict[str, Node] = {}
        for block in blocks:
            rules[block.block_type] = seq(
                f'{self.start_delimiter}\n---\nid: "',
                Ref(IDENTIFIER_RULE),
                f'"\nblock_type: {block.block_type}\n',
                *(self._field_line(metadata_field) for metadata_field in block.fields),
                "---\n",
                block.content(line),
                f"{self.end_delimiter}\n",
            )
        return SyntaxGrammar(
            text_line=line_not_starting_with(self.start_delimiter),
            blocks=rules,
            shared={**line.rules, IDENTIFIER_RULE: IDENTIFIER},
        )

    @staticmethod
    def _field_line(metadata_field: MetadataField) -> Node:
        """One ``name: value`` frontmatter line, optional when the field is."""
        if metadata_field.choices:
            value: Node = seq(*_quoted_choices(metadata_field.choices))
        else:
            string = quoted_string(_YAML_STRING_EXCLUDED, non_empty=metadata_field.non_empty)
            value = scalar(metadata_field, string=string)
        field_line = seq(f"{metadata_field.name}: ", value, "\n")
        return field_line if metadata_field.required else optional(field_line)


def _quoted_choices(choices: tuple[str, ...]) -> tuple[Node]:
    """Enum values as double-quoted YAML strings, so they are never read as another type."""
    return (Choice(tuple(Literal(f'"{value}"') for value in choices)),)
