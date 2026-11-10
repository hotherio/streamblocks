"""Tests for the built-in artifact blocks."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from hother.streamblocks import DelimiterFrontmatterSyntax, Registry, StreamBlockProcessor
from hother.streamblocks.blocks import (
    ARTIFACT_BLOCKS,
    DocumentArtifact,
    FileArtifact,
    PatchApplyError,
    PatchArtifact,
)
from hother.streamblocks.blocks.artifacts import (
    DocumentArtifactMetadata,
    FileArtifactMetadata,
    PatchArtifactContent,
)
from hother.streamblocks.core.types import BlockEndEvent, BlockErrorEvent

PATCH = """<<<<<<< SEARCH
    print("hello")
=======
    print("hello, world")
>>>>>>> REPLACE

<<<<<<< SEARCH
import os
=======
>>>>>>> REPLACE"""

SOURCE = 'import os\n\ndef main() -> None:\n    print("hello")\n'


def test_registry_mapping_uses_block_type_names() -> None:
    expected = {"file": FileArtifact, "patch": PatchArtifact, "document": DocumentArtifact}
    assert expected == ARTIFACT_BLOCKS


def test_file_metadata_defaults_and_validation() -> None:
    metadata = FileArtifactMetadata(id="a", path="src/a.py")
    assert (metadata.block_type, metadata.operation, metadata.language) == ("file", "create", None)
    with pytest.raises(ValidationError):
        FileArtifactMetadata(id="a", path="")


def test_document_metadata_defaults() -> None:
    metadata = DocumentArtifactMetadata(id="d", title="Guide")
    assert metadata.format == "markdown"


def test_patch_parses_hunks() -> None:
    content = PatchArtifactContent.parse(PATCH)
    assert [(h.search, h.replace) for h in content.hunks] == [
        ('    print("hello")', '    print("hello, world")'),
        ("import os", ""),
    ]
    assert content.raw_content == PATCH


def test_patch_applies_hunks_in_order() -> None:
    assert PatchArtifactContent.parse(PATCH).apply(SOURCE) == '\n\ndef main() -> None:\n    print("hello, world")\n'


@pytest.mark.parametrize(
    ("original", "matches"),
    [("def main() -> None:\n    pass\n", 0), (SOURCE + '    print("hello")\n', 2)],
)
def test_patch_apply_requires_exactly_one_match(original: str, matches: int) -> None:
    with pytest.raises(PatchApplyError, match=f"found {matches} times"):
        PatchArtifactContent.parse(PATCH).apply(original)


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        ("", "no search/replace hunk"),
        ("just prose", "outside a search/replace hunk"),
        ("<<<<<<< SEARCH\na\n=======\nb", "outside a search/replace hunk"),
        ("<<<<<<< SEARCH\na\n<<<<<<< SEARCH\nb\n=======\nc\n>>>>>>> REPLACE", "inside an open hunk"),
        ("<<<<<<< SEARCH\n=======\nb\n>>>>>>> REPLACE", "no search text"),
    ],
)
def test_patch_rejects_malformed_content(raw: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        PatchArtifactContent.parse(raw)


def test_examples_are_valid_blocks() -> None:
    for block_class in ARTIFACT_BLOCKS.values():
        assert block_class.get_examples()
    (patch_example,) = PatchArtifact.get_examples()
    assert patch_example.content.apply('def main() -> None:\n    print("hello")\n').endswith('print("hello, world")\n')


def test_artifacts_work_with_frontmatter_syntax() -> None:
    registry = Registry(syntax=DelimiterFrontmatterSyntax(), blocks=ARTIFACT_BLOCKS)
    processor = StreamBlockProcessor(registry)
    text = f"!!start\n---\nid: p1\nblock_type: patch\npath: src/main.py\n---\n{PATCH}\n!!end\n"
    events = [*processor.process_chunk(text), *processor.finalize()]
    (end,) = [e for e in events if isinstance(e, BlockEndEvent)]
    block = end.get_block()
    assert block is not None
    assert block.metadata.path == "src/main.py"
    assert len(block.content.hunks) == len(PatchArtifactContent.parse(PATCH).hunks)


def test_malformed_patch_block_is_rejected() -> None:
    registry = Registry(syntax=DelimiterFrontmatterSyntax(), blocks=ARTIFACT_BLOCKS)
    processor = StreamBlockProcessor(registry)
    text = "!!start\n---\nid: p1\nblock_type: patch\npath: a.py\n---\nnot a patch\n!!end\n"
    events = [*processor.process_chunk(text), *processor.finalize()]
    assert not [e for e in events if isinstance(e, BlockEndEvent)]
    assert [e for e in events if isinstance(e, BlockErrorEvent)]
