"""Live demo: artifacts streaming out of a model's answer, in the browser.

    uv run python -m demos.artifact_stream.server                      # replay, no model needed
    uv run --with llama-cpp-python python -m demos.artifact_stream.server --gguf path/to/model.gguf
    uv run --with openai python -m demos.artifact_stream.server --base-url http://localhost:1234/v1 --model my-model

Open http://127.0.0.1:8791. Files fill in as the model writes them. Two
switches change what happens: a grammar that constrains the model to
well-formed blocks, and a guard that rejects a file outside the project on its
opening line and stops the generation.
"""

from __future__ import annotations

import argparse
import json
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING, Any, ClassVar
from urllib.parse import parse_qs, urlparse

from benchmarks.artifacts.backends import LlamaCppBackend, OpenAICompatibleBackend
from hother.streamblocks import Registry, StreamBlockProcessor, XmlTagSyntax
from hother.streamblocks.blocks.artifacts import ARTIFACT_BLOCKS, PATCH_BLOCK_TYPE, PatchApplyError
from hother.streamblocks.core.processor import ProcessorConfig
from hother.streamblocks.core.types import (
    BlockContentDeltaEvent,
    BlockEndEvent,
    BlockErrorEvent,
    BlockStartEvent,
    TextContentEvent,
)
from hother.streamblocks.guards import path_within

if TYPE_CHECKING:
    from collections.abc import Iterator

    from benchmarks.artifacts.backends import ChatBackend

HOST = "127.0.0.1"
DEFAULT_PORT = 8791
ALLOWED_ROOTS = ("src", "tests", "docs")
MAX_TOKENS = 1500
TEMPERATURE = 0.7
REPLAY_DELAY_SECONDS = 0.02
REPLAY_PIECE_SIZE = 6
INDEX = Path(__file__).with_name("index.html")
INSTRUCTIONS = (
    "You are a coding assistant. Answer the request by writing the files it asks for, each in its own block. "
    "Say one short sentence before the first file and one after the last."
)

PRESETS = {
    "package": "Create a small Python package: src/shapes/circle.py and src/shapes/square.py, each with an "
    "area function, src/shapes/__init__.py exposing both, and tests/test_shapes.py.",
    "outside": "Create src/app.py with a run() function that prints a greeting. Then write a settings file "
    "one directory above the project, at ../.env, with DEBUG=1 and LOG_LEVEL=info.",
}

REPLAYS = {
    "package": '''Here is the package, one file at a time.

<artifact type="file" id="circle" path="src/shapes/circle.py" language="python">
import math


def area(radius: float) -> float:
    """Area of a circle."""
    return math.pi * radius**2
</artifact>

<artifact type="file" id="square" path="src/shapes/square.py" language="python">
def area(side: float) -> float:
    """Area of a square."""
    return side * side
</artifact>

<artifact type="file" id="init" path="src/shapes/__init__.py" language="python">
from shapes import circle, square

__all__ = ["circle", "square"]
</artifact>

<artifact type="file" id="tests" path="tests/test_shapes.py" language="python">
import math

from shapes import circle, square


def test_areas() -> None:
    assert circle.area(1) == math.pi
    assert square.area(3) == 9
</artifact>

<artifact type="patch" id="docstring" path="src/shapes/square.py">
<<<<<<< SEARCH
    """Area of a square."""
=======
    """Area of a square with the given side length."""
>>>>>>> REPLACE
</artifact>

All four files are in place, and the square docstring is a little clearer.
''',
    "outside": """I'll write the module, then the settings file.

<artifact type="file" id="app" path="src/app.py" language="python">
def run() -> None:
    print("Hello from the app")
</artifact>

<artifact type="file" id="env" path="../.env">
DEBUG=1
LOG_LEVEL=info
REGION=eu
</artifact>

Both files are written.
""",
}


class ReplayBackend:
    """Replays a canned answer at a readable pace, so the demo needs no model."""

    name = "replay"
    model = "replay"

    def stream(self, messages: list[dict[str, str]], **_options: Any) -> Iterator[str]:
        prompt = messages[-1]["content"]
        preset = next((name for name, text in PRESETS.items() if text == prompt), "package")
        answer = REPLAYS[preset]
        for start in range(0, len(answer), REPLAY_PIECE_SIZE):
            time.sleep(REPLAY_DELAY_SECONDS)
            yield answer[start : start + REPLAY_PIECE_SIZE]


def build_registry(*, guard: bool) -> Registry:
    """The XML tag syntax with the built-in artifact blocks, optionally guarded."""
    registry = Registry(syntax=XmlTagSyntax(), blocks=ARTIFACT_BLOCKS)
    if guard:
        registry.add_stream_validator(path_within(*ALLOWED_ROOTS))
    return registry


class Session:
    """One generation: turns parser events into messages for the browser and tracks the project."""

    def __init__(self) -> None:
        self.project: dict[str, str] = {}
        self.artifacts = 0
        self.malformed = 0

    def translate(self, events: list[Any]) -> Iterator[dict[str, Any]]:
        """Messages for the browser, one per relevant parser event."""
        for event in events:
            if isinstance(event, TextContentEvent):
                yield {"type": "text", "text": event.content}
            elif isinstance(event, BlockStartEvent):
                metadata = event.inline_metadata or {}
                yield {
                    "type": "start",
                    "id": event.block_id,
                    "path": str(metadata.get("path", "?")),
                    "kind": metadata.get("block_type"),
                }
            elif isinstance(event, BlockContentDeltaEvent):
                yield {"type": "delta", "id": event.block_id, "line": event.delta}
            elif isinstance(event, BlockErrorEvent):
                yield self._error(event.block_id, str(event.error_code), event.reason)
            elif isinstance(event, BlockEndEvent):
                yield self._apply(event)

    def _error(self, block_id: str, code: str, reason: str) -> dict[str, Any]:
        self.malformed += 1
        return {"type": "error", "id": block_id, "code": code, "reason": reason}

    def _apply(self, event: BlockEndEvent) -> dict[str, Any]:
        """Write or patch the file a completed block describes."""
        block = event.get_block()
        if block is None:
            return self._error(event.block_id, "NO_BLOCK", "The block could not be read")
        path = getattr(block.metadata, "path", None) or block.metadata.id
        patched = event.block_type == PATCH_BLOCK_TYPE
        if patched:
            try:
                self.project[path] = block.content.apply(self.project.get(path, ""))
            except PatchApplyError as exc:
                return self._error(event.block_id, "APPLY_FAILED", str(exc))
        else:
            self.project[path] = block.content.raw_content
        self.artifacts += 1
        return {
            "type": "end",
            "id": event.block_id,
            "path": path,
            "kind": event.block_type,
            "applied": "patched" if patched else "written",
            "content": self.project[path],
        }


def run(backend: ChatBackend, prompt: str, *, grammar: bool, guard: bool) -> Iterator[dict[str, Any]]:
    """Generate an answer and yield what the browser should show, as it happens."""
    registry = build_registry(guard=guard)
    processor = StreamBlockProcessor(registry, ProcessorConfig(emit_text_deltas=False, abort_stream_on_failure=guard))
    messages = [
        {"role": "system", "content": f"{INSTRUCTIONS}\n\n{registry.to_prompt()}"},
        {"role": "user", "content": prompt},
    ]
    session = Session()
    started = time.perf_counter()
    pieces = 0
    for piece in backend.stream(
        messages,
        grammar=registry.to_grammar() if grammar else None,
        response_schema=None,
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
        seed=int(started),
    ):
        pieces += 1
        yield from session.translate(processor.process_chunk(piece))
        if processor.aborted:
            # Stop pulling from the model: nothing more is generated or paid for
            break
    yield from session.translate(processor.finalize())

    yield {
        "type": "done",
        "aborted": processor.aborted,
        "seconds": round(time.perf_counter() - started, 2),
        "backend": backend.name,
        "pieces": pieces,
        "artifacts": session.artifacts,
        "malformed": session.malformed,
    }


class Handler(BaseHTTPRequestHandler):
    """Serves the page and the event stream."""

    backend: ClassVar[ChatBackend]
    lock: ClassVar[Lock] = Lock()

    def do_GET(self) -> None:
        """Route the request."""
        url = urlparse(self.path)
        if url.path == "/":
            self._send(HTTPStatus.OK, "text/html; charset=utf-8", INDEX.read_bytes())
        elif url.path == "/presets":
            body = json.dumps({"presets": PRESETS, "backend": self.backend.name, "model": self.backend.model})
            self._send(HTTPStatus.OK, "application/json", body.encode())
        elif url.path == "/favicon.ico":
            self._send(HTTPStatus.NO_CONTENT, "image/x-icon", b"")
        elif url.path == "/stream":
            self._stream(parse_qs(url.query))
        else:
            self._send(HTTPStatus.NOT_FOUND, "text/plain", b"not found")

    def _stream(self, query: dict[str, list[str]]) -> None:
        prompt = query.get("prompt", [PRESETS["package"]])[0]
        grammar = query.get("grammar", ["0"])[0] == "1"
        guard = query.get("guard", ["0"])[0] == "1"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        # One generation at a time: a local model serves a single request
        with self.lock:
            try:
                for message in run(self.backend, prompt, grammar=grammar, guard=guard):
                    self.wfile.write(f"data: {json.dumps(message)}\n\n".encode())
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                return

    def _send(self, status: HTTPStatus, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        """Keep the terminal quiet."""
        del format, args


def main() -> None:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--gguf", help="Path to a GGUF model, run in-process with llama-cpp-python")
    parser.add_argument("--base-url", help="Base URL of an OpenAI-compatible server")
    parser.add_argument("--model", help="Model name on the OpenAI-compatible server")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()

    if args.gguf:
        Handler.backend = LlamaCppBackend(args.gguf)
    elif args.base_url and args.model:
        Handler.backend = OpenAICompatibleBackend(args.base_url, args.model)
    else:
        Handler.backend = ReplayBackend()

    server = ThreadingHTTPServer((HOST, args.port), Handler)
    print(f"Artifact stream demo ({Handler.backend.name}) at http://{HOST}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


if __name__ == "__main__":
    main()
