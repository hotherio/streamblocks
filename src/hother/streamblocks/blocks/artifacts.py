"""Built-in artifact blocks: files, patches and documents written inside a response.

An artifact is output the reader wants to see being written (a file, an edit,
a document), as opposed to a tool call the model makes and waits on. These
blocks work with any syntax; :class:`~hother.streamblocks.syntaxes.xml.XmlTagSyntax`
and :class:`~hother.streamblocks.syntaxes.delimiter.DelimiterFrontmatterSyntax`
carry their metadata fields.

Example:
    >>> from hother.streamblocks import Registry, XmlTagSyntax
    >>> from hother.streamblocks.blocks.artifacts import ARTIFACT_BLOCKS
    >>> registry = Registry(syntax=XmlTagSyntax(), blocks=ARTIFACT_BLOCKS)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, ClassVar, Literal, Self, cast

from pydantic import BaseModel, Field, model_validator

from hother.streamblocks.core.models import Block
from hother.streamblocks.core.types import BaseContent, BaseMetadata

FileOperationLiteral = Literal["create", "overwrite"]
DocumentFormatLiteral = Literal["markdown", "text", "html"]

FILE_BLOCK_TYPE = "file"
PATCH_BLOCK_TYPE = "patch"
DOCUMENT_BLOCK_TYPE = "document"

type BlockExamples = list[dict[str, Any]] | Path | str

_SEARCH_MARKER = re.compile(r"^<{5,9} SEARCH[ \t]*$", re.MULTILINE)
_HUNK_PATTERN = re.compile(
    r"^<{5,9} SEARCH[ \t]*\n(?P<search>.*?)^={5,9}[ \t]*\n(?P<replace>.*?)^>{5,9} REPLACE[ \t]*$",
    re.MULTILINE | re.DOTALL,
)
_LINE_END = "\n"

# A hunk's search text must match exactly once in the text it is applied to
_EXPECTED_MATCHES = 1


class PatchApplyError(ValueError):
    """A patch hunk could not be applied to the given text."""


# ---------------------------------------------------------------------------
# File
# ---------------------------------------------------------------------------


class FileArtifactMetadata(BaseMetadata):
    """Metadata for file artifacts."""

    block_type: str = Field(default=FILE_BLOCK_TYPE, pattern=f"^{FILE_BLOCK_TYPE}$")
    path: str = Field(..., min_length=1, description="File path, relative to the project root")
    language: str | None = Field(default=None, description="Language of the file, for example python")
    operation: FileOperationLiteral = Field(default="create", description="create a new file or overwrite one")


class FileArtifactContent(BaseContent):
    """The complete file, written verbatim."""


class FileArtifact(Block[FileArtifactMetadata, FileArtifactContent]):
    """A complete file to write to disk.

    Usage: emit one file block per file, containing the whole file and nothing else.
    """

    __examples__: ClassVar[BlockExamples] = [
        {
            "metadata": {"id": "main", "block_type": "file", "path": "src/main.py", "language": "python"},
            "content": {"raw_content": 'def main() -> None:\n    print("hello")'},
        },
    ]


# ---------------------------------------------------------------------------
# Patch
# ---------------------------------------------------------------------------


class SearchReplaceHunk(BaseModel):
    """One edit: an exact piece of the current file and its replacement."""

    search: str = Field(..., min_length=1, description="Text to find, copied exactly from the file")
    replace: str = Field(..., description="Text that takes its place; empty deletes the search text")


def _require_blank(text: str) -> None:
    """Reject non-blank text found between or around hunks."""
    stripped = text.strip()
    if stripped:
        msg = f"Text outside a search/replace hunk: {stripped.splitlines()[0]!r}"
        raise ValueError(msg)


def _parse_hunks(raw_text: str) -> list[SearchReplaceHunk]:
    """Parse search/replace hunks, rejecting anything that is not one."""
    hunks: list[SearchReplaceHunk] = []
    position = 0
    for match in _HUNK_PATTERN.finditer(raw_text):
        _require_blank(raw_text[position : match.start()])
        search = match.group("search").removesuffix(_LINE_END)
        if not search:
            msg = "Hunk has no search text; use a file block to create a file"
            raise ValueError(msg)
        if _SEARCH_MARKER.search(search):
            msg = "SEARCH marker inside an open hunk"
            raise ValueError(msg)
        hunks.append(SearchReplaceHunk(search=search, replace=match.group("replace").removesuffix(_LINE_END)))
        position = match.end()

    _require_blank(raw_text[position:])
    if not hunks:
        msg = "Patch contains no search/replace hunk"
        raise ValueError(msg)
    return hunks


class PatchArtifactMetadata(BaseMetadata):
    """Metadata for patch artifacts."""

    block_type: str = Field(default=PATCH_BLOCK_TYPE, pattern=f"^{PATCH_BLOCK_TYPE}$")
    path: str = Field(..., min_length=1, description="Path of the file to edit, relative to the project root")


class PatchArtifactContent(BaseContent):
    """Search/replace hunks that edit an existing file."""

    hunks: list[SearchReplaceHunk] = Field(default_factory=list[SearchReplaceHunk])

    @model_validator(mode="before")
    @classmethod
    def _hunks_from_raw_content(cls, data: Any) -> Any:
        """Parse hunks from ``raw_content`` when they are not given explicitly."""
        if not isinstance(data, dict):
            return data
        fields = cast("dict[str, Any]", data)
        raw_content = fields.get("raw_content")
        if "hunks" in fields or not isinstance(raw_content, str):
            return fields
        return {**fields, "hunks": _parse_hunks(raw_content)}

    @classmethod
    def parse(cls, raw_text: str) -> Self:
        """One or more search/replace hunks, each written as:

        <<<<<<< SEARCH
        lines copied exactly from the current file
        =======
        lines that replace them
        >>>>>>> REPLACE

        Raises:
            ValueError: If a hunk is malformed, or no hunk is present
        """
        return cls(raw_content=raw_text)

    def apply(self, original: str) -> str:
        """Apply every hunk, in order, to ``original`` and return the edited text.

        Each hunk's search text must occur exactly once in the text at the time
        it is applied.

        Raises:
            PatchApplyError: If a search text is missing or occurs more than once
        """
        text = original
        for index, hunk in enumerate(self.hunks, start=1):
            matches = text.count(hunk.search)
            if matches != _EXPECTED_MATCHES:
                msg = f"Hunk {index}: search text found {matches} times, expected {_EXPECTED_MATCHES}"
                raise PatchApplyError(msg)
            text = text.replace(hunk.search, hunk.replace)
        return text


class PatchArtifact(Block[PatchArtifactMetadata, PatchArtifactContent]):
    """An edit to an existing file, as search/replace hunks.

    Usage: prefer a patch over a file block when changing a small part of an existing file.
    """

    __examples__: ClassVar[BlockExamples] = [
        {
            "metadata": {"id": "fix-greeting", "block_type": "patch", "path": "src/main.py"},
            "content": {
                "raw_content": (
                    '<<<<<<< SEARCH\n    print("hello")\n=======\n    print("hello, world")\n>>>>>>> REPLACE'
                ),
            },
        },
    ]


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------


class DocumentArtifactMetadata(BaseMetadata):
    """Metadata for document artifacts."""

    block_type: str = Field(default=DOCUMENT_BLOCK_TYPE, pattern=f"^{DOCUMENT_BLOCK_TYPE}$")
    title: str = Field(..., min_length=1, description="Title of the document")
    format: DocumentFormatLiteral = Field(default="markdown", description="markdown, text or html")


class DocumentArtifactContent(BaseContent):
    """The complete document, written verbatim."""


class DocumentArtifact(Block[DocumentArtifactMetadata, DocumentArtifactContent]):
    """A standalone document such as a report, a guide or a page.

    Usage: emit a document block for long-form content the reader will keep, not for a short answer.
    """

    __examples__: ClassVar[BlockExamples] = [
        {
            "metadata": {"id": "release-notes", "block_type": "document", "title": "Release notes"},
            "content": {"raw_content": "# Release notes\n\n- Faster parsing"},
        },
    ]


ARTIFACT_BLOCKS: dict[str, type[Block[Any, Any]]] = {
    "file": FileArtifact,
    "patch": PatchArtifact,
    "document": DocumentArtifact,
}
"""Block type name to block class, ready for ``Registry(blocks=ARTIFACT_BLOCKS)``."""
