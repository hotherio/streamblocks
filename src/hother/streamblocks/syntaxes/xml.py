"""XML tag syntax implementation."""

from __future__ import annotations

import hashlib
import re
from html import escape, unescape
from typing import TYPE_CHECKING, Any

from hother.streamblocks.core.models import extract_block_types
from hother.streamblocks.core.types import BaseContent, BaseMetadata, DetectionResult, ParseResult
from hother.streamblocks.syntaxes.base import BaseSyntax

if TYPE_CHECKING:
    from hother.streamblocks.core.models import Block, BlockCandidate, ExtractedBlock

# Minimum lines required for a block (opening tag + closing tag)
_MIN_BLOCK_LINES = 2

# Attribute carrying the block type, and attribute carrying the block identifier
_TYPE_ATTRIBUTE = "type"
_ID_ATTRIBUTE = "id"

# Size in bytes of the digest used to derive an id when the tag carries none
_GENERATED_ID_DIGEST_SIZE = 4

_TAG_NAME_PATTERN = re.compile(r"^[A-Za-z_][\w.-]*$")
_ATTRIBUTE_PATTERN = re.compile(r"""([\w:.-]+)\s*=\s*(?:"([^"]*)"|'([^']*)')""")
_SELF_CLOSING_SUFFIX = "/"


class XmlTagSyntax(BaseSyntax):
    """Syntax: an XML-style tag whose attributes carry the metadata.

    Format:
        <artifact type="file" id="main" path="src/main.py">
        Content lines here, written verbatim
        </artifact>

    The opening and closing tags must each sit on their own line. The ``type``
    attribute selects the block type (it defaults to the tag name) and every
    other attribute becomes a metadata field. When the tag has no ``id``
    attribute, a stable id is derived from the opening line.

    Attribute values are XML-unescaped (``&quot;``, ``&amp;``...). Content is
    never unescaped, so code can be written as is.

    Examples:
        >>> syntax = XmlTagSyntax()
        >>> syntax.detect_line('<artifact type="file" path="a.py">').metadata
        {'path': 'a.py', 'block_type': 'file', 'id': 'artifact-...'}

    Args:
        tag: Tag name (default: "artifact")
        lenient_close: Treat a closing tag followed by text on the same line as
            a close, and re-process that text as a new line (default: True)
    """

    def __init__(self, tag: str = "artifact", *, lenient_close: bool = True) -> None:
        """Initialize XML tag syntax.

        Args:
            tag: Tag name to detect
            lenient_close: Accept text after the closing tag on the same line

        Raises:
            ValueError: If ``tag`` is not a valid tag name
        """
        if not _TAG_NAME_PATTERN.match(tag):
            msg = f"Invalid tag name: {tag!r}"
            raise ValueError(msg)

        self.tag = tag
        self.lenient_close = lenient_close
        escaped_tag = re.escape(tag)
        self._opening_pattern = re.compile(rf"^\s*<{escaped_tag}(?P<attributes>(?:\s[^<>]*)?)>\s*$")
        self._closing_pattern = re.compile(rf"^\s*</{escaped_tag}\s*>(?P<rest>.*)$")

    def _parse_opening(self, line: str) -> dict[str, str] | None:
        """Return the metadata carried by an opening tag line, or None if it is not one."""
        match = self._opening_pattern.match(line)
        if match is None:
            return None

        raw_attributes = match.group("attributes")
        if raw_attributes.rstrip().endswith(_SELF_CLOSING_SUFFIX):
            return None

        metadata: dict[str, str] = {}
        for attribute in _ATTRIBUTE_PATTERN.finditer(raw_attributes):
            name, double_quoted, single_quoted = attribute.groups()
            metadata[name] = unescape(double_quoted if double_quoted is not None else single_quoted)

        metadata["block_type"] = metadata.pop(_TYPE_ATTRIBUTE, self.tag)
        if not metadata.get(_ID_ATTRIBUTE):
            digest = hashlib.blake2s(line.strip().encode(), digest_size=_GENERATED_ID_DIGEST_SIZE).hexdigest()
            metadata[_ID_ATTRIBUTE] = f"{self.tag}-{digest}"
        return metadata

    def detect_line(self, line: str, candidate: BlockCandidate | None = None) -> DetectionResult:
        """Detect opening and closing tags."""
        if candidate is None:
            metadata = self._parse_opening(line)
            if metadata is None:
                return DetectionResult()
            return DetectionResult(is_opening=True, metadata=dict(metadata))

        closing = self._closing_pattern.match(line)
        if closing is not None:
            rest = closing.group("rest").strip()
            if not rest:
                return DetectionResult(is_closing=True)
            if self.lenient_close:
                return DetectionResult(is_closing=True, remainder=rest)

        candidate.transition_to_content()
        candidate.content_lines.append(line)
        return DetectionResult()

    def should_accumulate_metadata(self, candidate: BlockCandidate) -> bool:
        """Metadata lives in the opening tag; there is no metadata section."""
        return False

    def extract_block_type(self, candidate: BlockCandidate) -> str | None:
        """Extract block_type from the opening tag."""
        metadata = self._parse_opening(candidate.lines[0]) if candidate.lines else None
        return metadata["block_type"] if metadata else None

    def parse_block(
        self, candidate: BlockCandidate, block_class: type[Any] | None = None
    ) -> ParseResult[BaseMetadata, BaseContent]:
        """Parse the complete block using the specified block class."""
        if block_class is None:
            metadata_class: type[BaseMetadata] = BaseMetadata
            content_class: type[BaseContent] = BaseContent
        else:
            metadata_class, content_class = extract_block_types(block_class)

        raw_metadata = self._parse_opening(candidate.lines[0]) if candidate.lines else None
        if raw_metadata is None:
            return ParseResult(success=False, error="Missing or invalid opening tag")

        metadata = self._safe_parse_metadata(metadata_class, dict(raw_metadata))
        if isinstance(metadata, ParseResult):
            return metadata

        content = self._safe_parse_content(content_class, "\n".join(candidate.lines[1:-1]))
        if isinstance(content, ParseResult):
            return content

        return ParseResult(success=True, metadata=metadata, content=content)

    def validate_block(self, _block: ExtractedBlock[BaseMetadata, BaseContent]) -> bool:
        """Additional validation after parsing."""
        return True

    def parse_metadata_early(self, candidate: BlockCandidate) -> dict[str, Any] | None:
        """Parse metadata from the opening tag."""
        metadata = self._parse_opening(candidate.lines[0]) if candidate.lines else None
        return dict(metadata) if metadata else None

    def parse_content_early(self, candidate: BlockCandidate) -> dict[str, Any] | None:
        """Return the raw content accumulated between the tags."""
        if len(candidate.lines) < _MIN_BLOCK_LINES:
            return None
        return {"raw_content": "\n".join(candidate.lines[1:-1])}

    def serialize_block(self, block: Block[BaseMetadata, BaseContent]) -> str:
        """Serialize a block to XML tag format.

        Produces the round-trip form of this syntax::

            <artifact type="<type>" id="<id>" key="value">
            <raw content>
            </artifact>

        Args:
            block: Block instance to serialize

        Returns:
            The block rendered in XML tag format
        """
        fields = block.metadata.model_dump(mode="json", exclude_none=True)
        attributes: dict[str, Any] = {
            _TYPE_ATTRIBUTE: fields.pop("block_type"),
            _ID_ATTRIBUTE: fields.pop(_ID_ATTRIBUTE),
            **fields,
        }
        rendered = " ".join(f'{name}="{escape(str(value), quote=True)}"' for name, value in attributes.items())
        return f"<{self.tag} {rendered}>\n{block.content.raw_content}\n</{self.tag}>"

    def describe_format(self) -> str:
        """Describe the XML tag format for prompts."""
        return (
            "XML Tag Syntax\n\n"
            "Format:\n"
            f'<{self.tag} type="<type>" id="<id>" key="value">\n'
            "content lines\n"
            f"</{self.tag}>\n\n"
            "Components:\n"
            f"- Opening tag: <{self.tag} ...> alone on its own line; type identifies the block, id is unique\n"
            '- Attributes: every other key="value" pair is a metadata field of the block\n'
            "- Content: the lines between the tags, written verbatim with no escaping\n"
            f"- Closing tag: </{self.tag}> alone on its own line"
        )
