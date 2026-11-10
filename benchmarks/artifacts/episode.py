"""Run one benchmark episode and describe it as a JSON-serialisable record."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from benchmarks.artifacts.arms import Arm
    from benchmarks.artifacts.backends import ChatBackend
    from benchmarks.artifacts.tasks import Task

RECORD_VERSION = 1


@dataclass
class Episode:
    """One answer to one task under one arm.

    The first group of fields is shared with the reactive benchmarks, which
    fill the fields this benchmark leaves as None.

    Attributes:
        artifacts: Artifacts extracted and applied
        malformed_by_code: Failures by code (parser error codes, APPLY_FAILED, INVALID_JSON, NO_ARTIFACT)
        well_formed: At least one artifact, and no failure of any kind
        score: 1.0 if the task check passed, else 0.0
        completion_tokens: Pieces generated (one piece is about one token)
        truncated: The answer hit the token limit
        first_artifact_piece: Piece index at which the application first learned an artifact was coming
        ttfa_s: Seconds until that point
        error: Backend error, if the episode could not run
    """

    backend: str
    model: str
    arm: str
    task: str
    family: str
    seed: int
    grammar: bool
    artifacts: int = 0
    malformed_by_code: dict[str, int] = field(default_factory=dict[str, int])
    well_formed: bool = False
    score: float = 0.0
    completion_tokens: int = 0
    truncated: bool = False
    first_artifact_piece: int | None = None
    ttfa_s: float | None = None
    total_s: float = 0.0
    tokens_per_s: float = 0.0
    error: str | None = None
    answer: str = ""
    record_version: int = RECORD_VERSION
    # Filled by the reactive benchmarks only
    delivery: str | None = None
    event_at_token: int | None = None
    delivered_at_token: int | None = None
    reaction_latency_tokens: int | None = None
    wasted_tokens: int | None = None
    llm_calls: int | None = None
    resent_prompt_tokens: int | None = None
    compliant: bool | None = None
    stale_actions: int | None = None
    virtual_time_s: float | None = None

    def to_record(self) -> dict[str, Any]:
        """The episode as a JSON-serialisable dict."""
        return asdict(self)


def run_episode(
    backend: ChatBackend,
    arm: Arm,
    task: Task,
    *,
    seed: int,
    max_tokens: int,
    temperature: float,
) -> Episode:
    """Generate one answer, read it back through the arm, and score it."""
    episode = Episode(
        backend=backend.name,
        model=backend.model,
        arm=arm.name,
        task=task.name,
        family=task.family,
        seed=seed,
        grammar=arm.grammar is not None or arm.response_schema is not None,
    )
    reader = arm.new_reader(task)
    pieces: list[str] = []
    started = time.perf_counter()
    first_artifact_at: float | None = None
    try:
        for piece in backend.stream(
            arm.messages(task),
            grammar=arm.grammar,
            response_schema=arm.response_schema,
            max_tokens=max_tokens,
            temperature=temperature,
            seed=seed,
        ):
            # A model can emit half of a multi-byte character; keep the text encodable
            text = piece.encode("utf-8", "replace").decode("utf-8")
            pieces.append(text)
            reader.feed(text)
            if first_artifact_at is None and _first_artifact(reader) is not None:
                first_artifact_at = time.perf_counter()
    except Exception as exc:  # a backend failure is recorded, not raised, so a sweep keeps going
        episode.error = f"{type(exc).__name__}: {exc}"
    extraction = reader.finish()
    finished = time.perf_counter()

    episode.answer = "".join(pieces)
    episode.completion_tokens = len(pieces)
    episode.truncated = len(pieces) >= max_tokens
    episode.total_s = finished - started
    episode.tokens_per_s = len(pieces) / episode.total_s if episode.total_s else 0.0
    episode.artifacts = extraction.artifacts
    episode.malformed_by_code = dict(extraction.malformed)
    episode.well_formed = extraction.artifacts > 0 and not extraction.malformed
    episode.first_artifact_piece = extraction.first_artifact_piece
    if extraction.first_artifact_piece is not None:
        episode.ttfa_s = (first_artifact_at if first_artifact_at is not None else finished) - started
    if episode.error is None:
        try:
            episode.score = float(task.check(extraction.project))
        except Exception as exc:  # a check that cannot run is a failed episode, not a failed sweep
            episode.error = f"check failed: {type(exc).__name__}: {exc}"
    return episode


def _first_artifact(reader: Any) -> int | None:
    """The reader's first-artifact piece index while streaming, when it tracks one."""
    extraction = getattr(reader, "_extraction", None)
    return getattr(extraction, "first_artifact_piece", None)
