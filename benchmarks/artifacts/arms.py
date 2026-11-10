"""Benchmark arms: ways of asking a model for files, and of reading them back.

Block arms use StreamBlocks (a syntax, the built-in file and patch blocks,
optionally a grammar). The two baselines are what people do without it:
fenced code blocks read back with a regular expression, and a JSON object whose
strings hold the file contents (how tool-call arguments carry files).
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

from hother.streamblocks import Block, DelimiterFrontmatterSyntax, Registry, StreamBlockProcessor, XmlTagSyntax
from hother.streamblocks.blocks.artifacts import (
    FILE_BLOCK_TYPE,
    PATCH_BLOCK_TYPE,
    FileArtifact,
    PatchApplyError,
    PatchArtifact,
)
from hother.streamblocks.core.processor import ProcessorConfig
from hother.streamblocks.core.types import BlockEndEvent, BlockErrorEvent, BlockStartEvent

if TYPE_CHECKING:
    from benchmarks.artifacts.tasks import Project, Task

_INSTRUCTIONS = (
    "You are a coding assistant. Answer the request by writing the files it asks for. "
    "Keep any explanation to one short sentence."
)
_FENCE_PATTERN = re.compile(r"^```(?P<path>[^\s`]+)[ \t]*\n(?P<content>.*?)^```[ \t]*$", re.MULTILINE | re.DOTALL)
_APPLY_FAILED = "APPLY_FAILED"
_INVALID_JSON = "INVALID_JSON"
_NO_ARTIFACT = "NO_ARTIFACT"

JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "files": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                "required": ["path", "content"],
            },
        }
    },
    "required": ["files"],
}


@dataclass
class Extraction:
    """What an arm read back from a model's answer.

    Attributes:
        project: The project after applying the answer to the task's initial files
        artifacts: Number of artifacts extracted and applied
        malformed: Count of failures by code (parser error codes, plus apply and JSON failures)
        first_artifact_piece: Index of the piece at which the first artifact started to be
            available to the application, or None if none was
    """

    project: Project
    artifacts: int = 0
    malformed: Counter[str] = field(default_factory=Counter[str])
    first_artifact_piece: int | None = None


class Reader(Protocol):
    """Consumes an answer piece by piece and reports what it contained."""

    def feed(self, piece: str) -> None:
        """Consume the next piece of the answer."""
        ...

    def finish(self) -> Extraction:
        """Return what the whole answer contained."""
        ...


@dataclass(frozen=True)
class Arm:
    """One way of asking for files.

    Attributes:
        name: Arm name
        grammar: GBNF grammar constraining the answer, if any
        response_schema: JSON schema constraining the answer, if any
    """

    name: str
    system: str
    reader: type[Reader] | Any
    grammar: str | None = None
    response_schema: dict[str, Any] | None = None

    def messages(self, task: Task) -> list[dict[str, str]]:
        """The conversation that asks for ``task``."""
        existing = "".join(
            f"\nCurrent content of `{path}`:\n-----\n{text}-----\n" for path, text in task.initial_files.items()
        )
        return [{"role": "system", "content": self.system}, {"role": "user", "content": task.prompt + existing}]

    def new_reader(self, task: Task) -> Reader:
        """A fresh reader for one answer to ``task``."""
        return self.reader(dict(task.initial_files))


class BlockReader:
    """Reads file and patch blocks as they stream."""

    registry: Registry

    def __init__(self, project: Project) -> None:
        self._extraction = Extraction(project=project)
        self._processor = StreamBlockProcessor(self.registry, ProcessorConfig(emit_text_deltas=False))
        self._pieces = 0

    def feed(self, piece: str) -> None:
        self._pieces += 1
        self._handle(self._processor.process_chunk(piece))

    def finish(self) -> Extraction:
        self._handle(self._processor.finalize())
        if not self._extraction.artifacts and not self._extraction.malformed:
            self._extraction.malformed[_NO_ARTIFACT] += 1
        return self._extraction

    def _handle(self, events: list[Any]) -> None:
        extraction = self._extraction
        for event in events:
            if isinstance(event, BlockStartEvent) and extraction.first_artifact_piece is None:
                extraction.first_artifact_piece = self._pieces
            elif isinstance(event, BlockErrorEvent):
                extraction.malformed[str(event.error_code)] += 1
            elif isinstance(event, BlockEndEvent):
                self._apply(event)

    def _apply(self, event: BlockEndEvent) -> None:
        extraction = self._extraction
        block = event.get_block()
        if block is None or event.block_type not in {FILE_BLOCK_TYPE, PATCH_BLOCK_TYPE}:
            extraction.malformed[_APPLY_FAILED] += 1
            return
        path = block.metadata.path
        if event.block_type == FILE_BLOCK_TYPE:
            extraction.project[path] = block.content.raw_content
        else:
            try:
                extraction.project[path] = block.content.apply(extraction.project.get(path, ""))
            except PatchApplyError:
                extraction.malformed[_APPLY_FAILED] += 1
                return
        extraction.artifacts += 1


class FencedReader:
    """Reads fenced code blocks whose info string is the path, once the answer is complete."""

    def __init__(self, project: Project) -> None:
        self._project = project
        self._text: list[str] = []

    def feed(self, piece: str) -> None:
        self._text.append(piece)

    def finish(self) -> Extraction:
        extraction = Extraction(project=self._project)
        for match in _FENCE_PATTERN.finditer("".join(self._text)):
            extraction.project[match.group("path")] = match.group("content").removesuffix("\n")
            extraction.artifacts += 1
        if not extraction.artifacts:
            extraction.malformed[_NO_ARTIFACT] += 1
        else:
            extraction.first_artifact_piece = len(self._text)
        return extraction


class JsonReader:
    """Reads one JSON object listing files, once the answer is complete."""

    def __init__(self, project: Project) -> None:
        self._project = project
        self._text: list[str] = []

    def feed(self, piece: str) -> None:
        self._text.append(piece)

    def finish(self) -> Extraction:
        extraction = Extraction(project=self._project)
        text = "".join(self._text).strip()
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            files = json.loads(text)["files"]
            for entry in files:
                extraction.project[str(entry["path"])] = str(entry["content"]).removesuffix("\n")
                extraction.artifacts += 1
        except (ValueError, KeyError, TypeError):
            extraction.malformed[_INVALID_JSON] += 1
            return extraction
        if not extraction.artifacts:
            extraction.malformed[_NO_ARTIFACT] += 1
        else:
            extraction.first_artifact_piece = len(self._text)
        return extraction


def _block_arm(name: str, registry: Registry, *, examples: bool, grammar: bool) -> Arm:
    reader = type(f"{name}Reader", (BlockReader,), {"registry": registry})
    prompt = registry.to_prompt(include_examples=examples)
    return Arm(
        name=name,
        system=f"{_INSTRUCTIONS}\n\n{prompt}",
        reader=reader,
        grammar=registry.to_grammar() if grammar else None,
    )


def build_arms() -> dict[str, Arm]:
    """Every arm, by name."""
    blocks: dict[str, type[Block[Any, Any]]] = {FILE_BLOCK_TYPE: FileArtifact, PATCH_BLOCK_TYPE: PatchArtifact}
    xml = Registry(syntax=XmlTagSyntax(), blocks=blocks)
    frontmatter = Registry(syntax=DelimiterFrontmatterSyntax(), blocks=blocks)
    fenced_system = (
        f"{_INSTRUCTIONS}\n\nWrite each file as a fenced code block whose info string is the file path, "
        "for example:\n\n```src/main.py\nprint('hello')\n```\n\nAlways write the complete file."
    )
    json_system = (
        f"{_INSTRUCTIONS}\n\nAnswer with a single JSON object and nothing else, of the form "
        '{"files": [{"path": "src/main.py", "content": "print(\'hello\')\\n"}]}. '
        "Always give the complete content of each file."
    )
    arms = [
        _block_arm("xml", xml, examples=True, grammar=False),
        _block_arm("xml+grammar", xml, examples=True, grammar=True),
        _block_arm("xml-noex", xml, examples=False, grammar=False),
        _block_arm("xml-noex+grammar", xml, examples=False, grammar=True),
        _block_arm("frontmatter", frontmatter, examples=True, grammar=False),
        _block_arm("frontmatter+grammar", frontmatter, examples=True, grammar=True),
        Arm(name="fenced", system=fenced_system, reader=FencedReader),
        Arm(name="json", system=json_system, reader=JsonReader),
        Arm(name="json+schema", system=json_system, reader=JsonReader, response_schema=JSON_SCHEMA),
    ]
    return {arm.name: arm for arm in arms}
