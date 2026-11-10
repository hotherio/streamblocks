"""Parser-only benchmark (no model): correctness under arbitrary chunking, and throughput.

    uv run python -m benchmarks.artifacts.parser_bench

A synthetic answer with many artifacts is split at random positions and parsed.
StreamBlocks must extract the same artifacts whatever the split. The baseline
is what an application typically writes by hand: a regular expression run on
the accumulated text every time a chunk arrives.
"""

from __future__ import annotations

import re
import time
from itertools import pairwise
from random import Random

from hother.streamblocks import Registry, StreamBlockProcessor, XmlTagSyntax
from hother.streamblocks.blocks.artifacts import ARTIFACT_BLOCKS
from hother.streamblocks.core.processor import ProcessorConfig
from hother.streamblocks.core.types import BlockEndEvent

_ARTIFACTS = 400
_LINES_PER_ARTIFACT = 40
_CHUNKINGS = 20
_MEAN_CHUNK = 24
_SEED = 0
_MEGABYTE = 1_000_000
_BASELINE_PATTERN = re.compile(
    r'^<artifact type="file" id="(?P<id>[^"]+)" path="(?P<path>[^"]+)">\n(?P<content>.*?)^</artifact>$',
    re.MULTILINE | re.DOTALL,
)


def build_answer(artifacts: int = _ARTIFACTS, lines: int = _LINES_PER_ARTIFACT) -> str:
    """A long answer: prose, then a file artifact, repeated."""
    parts: list[str] = []
    for index in range(artifacts):
        body = "\n".join(f'    value_{line} = "<tag> & {line}"  # line {line}' for line in range(lines))
        parts.append(f"Here is module {index}.\n")
        parts.append(
            f'<artifact type="file" id="m{index}" path="src/m{index}.py">\ndef f() -> None:\n{body}\n</artifact>\n'
        )
    return "".join(parts)


def chunked(text: str, rng: Random, mean: int = _MEAN_CHUNK) -> list[str]:
    """Split ``text`` at random positions, with chunks of about ``mean`` characters."""
    cuts = sorted(rng.sample(range(1, len(text)), k=len(text) // mean))
    return [text[a:b] for a, b in pairwise([0, *cuts, len(text)])]


def extract_streaming(chunks: list[str]) -> list[tuple[str, str]]:
    """Artifacts as (path, content), extracted with StreamBlocks while chunks arrive."""
    registry = Registry(syntax=XmlTagSyntax(), blocks=ARTIFACT_BLOCKS)
    processor = StreamBlockProcessor(registry, ProcessorConfig(emit_text_deltas=False))
    events = [event for chunk in chunks for event in processor.process_chunk(chunk)]
    events.extend(processor.finalize())
    return [(str(e.metadata["path"]), str(e.content["raw_content"])) for e in events if isinstance(e, BlockEndEvent)]


def extract_rescan(chunks: list[str]) -> list[tuple[str, str]]:
    """The hand-written baseline: re-scan the accumulated text after every chunk."""
    text = ""
    found: list[tuple[str, str]] = []
    for chunk in chunks:
        text += chunk
        found = [(m.group("path"), m.group("content").removesuffix("\n")) for m in _BASELINE_PATTERN.finditer(text)]
    return found


def main() -> None:
    """Check chunking invariance, then time both extractors."""
    answer = build_answer()
    rng = Random(_SEED)
    reference = extract_streaming([answer])
    assert len(reference) == _ARTIFACTS

    for _ in range(_CHUNKINGS):
        assert extract_streaming(chunked(answer, rng)) == reference
    print(f"chunking invariance: {_ARTIFACTS} artifacts identical across {_CHUNKINGS} random chunkings")

    chunks = chunked(answer, rng)
    size = len(answer) / _MEGABYTE
    started = time.perf_counter()
    extract_streaming(chunks)
    streaming = time.perf_counter() - started
    print(f"streamblocks:      {size / streaming:6.1f} MB/s ({len(chunks)} chunks, {size:.2f} MB)")

    # The baseline is quadratic, so it is timed on a tenth of the answer
    small = chunked(build_answer(_ARTIFACTS // 10), rng)
    small_size = sum(map(len, small)) / _MEGABYTE
    started = time.perf_counter()
    assert len(extract_rescan(small)) == _ARTIFACTS // 10
    rescan = time.perf_counter() - started
    print(
        f"regex re-scan:     {small_size / rescan:6.1f} MB/s on {small_size:.2f} MB (cost grows with the square of the length)"
    )


if __name__ == "__main__":
    main()
