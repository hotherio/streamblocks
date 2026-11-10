"""Mid-turn steering: a correction arrives while the model is writing a guide.

The model writes steps as blocks. Once `event_after_step` steps are closed, an event
block becomes available and is delivered one of three ways (`Delivery`). Later step
blocks override earlier ones with the same id, and a regex check scores the final guide.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

from hother.streamblocks import DelimiterPreambleSyntax, Registry, StreamBlockProcessor
from hother.streamblocks.core.processor import ProcessorConfig
from hother.streamblocks.core.types import BlockEndEvent, BlockErrorEvent, BlockStartEvent

if TYPE_CHECKING:
    from benchmarks.reactive.backend import Backend, Message

STEP = "step"
# Without this, a model cut off mid-guide treats the event as a new request, fixes old steps and stops.
INTERRUPTED_NOTE = "Your output was interrupted by this event. Continue the guide where you stopped."
SYSTEM_PROMPT = """You write guides as step blocks, and nothing outside blocks. Each block is exactly:

!!s<N>:step
<text of step N>
!!end

Every block ends with a line containing only !!end, before the next block starts. \
Example of a two-step guide:

!!s1:step
Boil the water.
!!end
!!s2:step
Pour it over the tea leaves.
!!end

The environment can send you an event block at any moment, even in the middle of your own output:

!!e<N>:event
<instruction>
!!end

Never write an event block yourself. When one appears, obey it at once: every step you write after it \
must respect it. If a step you already wrote contradicts it, write that step again with the same id. \
Do not repeat steps that are still valid. Stop after the last step."""


class Delivery(StrEnum):
    """How the event reaches the model."""

    TURN_BOUNDARY = "turn_boundary"  # as a new user turn, after the model finished
    CANCEL_RESEND = "cancel_resend"  # stop the model, send a new user turn
    INJECT = "inject"  # appended to the model's own turn, generation continues


@dataclass(frozen=True)
class Scenario:
    name: str
    task: str
    event: str
    forbidden: str
    required: str
    steps: int = 6
    event_after_step: int = 2

    @property
    def event_block(self) -> str:
        return f"!!e1:event\n{self.event}\n!!end\n"


SCENARIOS = [
    Scenario(
        "database",
        "Write a 6-step guide to set up a small Flask todo app that stores its data in SQLite. Every step must name the database it uses.",
        "Change of plan: the database is PostgreSQL, not SQLite.",
        forbidden=r"sqlite",
        required=r"postgres",
    ),
    Scenario(
        "installer",
        "Write a 6-step guide to start a Python project using pip for all installs. Every step must show the exact command to run.",
        "Use uv instead of pip in every command.",
        forbidden=r"\bpip\b",
        required=r"\buv\b",
    ),
    Scenario(
        "port",
        "Write a 6-step guide to run and test a local HTTP API on port 8000. Every step must include a full URL with the port.",
        "The service must listen on port 9090, not 8000.",
        forbidden=r"8000",
        required=r"9090",
    ),
    Scenario(
        "rename",
        "Write a 6-step guide to create and publish a command-line tool named acme. Every step must mention the tool by name.",
        "The tool is renamed zenith. Do not use the old name.",
        forbidden=r"\bacme\b",
        required=r"\bzenith\b",
    ),
    Scenario(
        "language",
        "Write a 6-step guide to build a hello-world web server in Python. Every step must name the language.",
        "Write it in Go instead of Python.",
        forbidden=r"python",
        required=r"\bgo\b|golang",
    ),
]


@dataclass
class Episode:
    """One run. Field names follow the shared benchmark episode record."""

    task: str
    delivery: str
    compliant: bool = False
    steps_present: int = 0
    event_at_token: int | None = None
    delivered_at_token: int | None = None
    reaction_latency_tokens: int | None = None
    wasted_tokens: int = 0
    completion_tokens: int = 0
    llm_calls: int = 1
    resent_prompt_tokens: int = 0
    uncached_prompt_tokens: int = 0
    malformed_blocks: int = 0
    transcript: str = ""
    guide: dict[str, str] = field(default_factory=dict[str, str])


def run_episode(backend: Backend, scenario: Scenario, delivery: Delivery, *, max_tokens: int = 1500) -> Episode:
    return _Run(backend, scenario, delivery).run(max_tokens)


class _Run:
    def __init__(self, backend: Backend, scenario: Scenario, delivery: Delivery) -> None:
        self.backend = backend
        self.scenario = scenario
        self.delivery = delivery
        self.episode = Episode(task=scenario.name, delivery=delivery.value)
        self.processor = StreamBlockProcessor(
            Registry(syntax=DelimiterPreambleSyntax()),
            ProcessorConfig(emit_text_deltas=False, emit_original_events=False, auto_detect_adapter=False),
        )
        self.messages: list[Message] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": scenario.task},
        ]
        self.turn: list[str] = []
        self.transcript: list[str] = []
        self.step_tokens: dict[str, int] = {}  # tokens of the latest version of each step written after the event
        self.steps_closed = 0
        self.line_started_at = 0  # completion tokens when the current line began
        self.block_started_at = 0
        self.inside_block = False

    def run(self, max_tokens: int) -> Episode:
        episode, backend = self.episode, self.backend
        prompt_before, uncached_before = backend.prompt_tokens, backend.uncached_prompt_tokens
        backend.begin(self.messages)

        while episode.completion_tokens < max_tokens:
            piece = backend.next_piece()
            if piece is None:
                self.feed("\n")
                if not self.event_pending:
                    break
                self.deliver_as_new_turn()
                continue
            episode.completion_tokens += 1
            self.turn.append(piece)
            self.feed(piece)
            if episode.event_at_token is None and self.steps_closed >= self.scenario.event_after_step:
                episode.event_at_token = episode.completion_tokens
            at_boundary = piece.endswith("\n") and not self.inside_block
            if self.event_pending and at_boundary and self.delivery is not Delivery.TURN_BOUNDARY:
                self.deliver_now()

        episode.malformed_blocks += sum(isinstance(e, BlockErrorEvent) for e in self.processor.finalize())
        if episode.event_at_token is not None and episode.delivered_at_token is not None:
            episode.reaction_latency_tokens = episode.delivered_at_token - episode.event_at_token
        episode.resent_prompt_tokens = backend.prompt_tokens - prompt_before
        episode.uncached_prompt_tokens = backend.uncached_prompt_tokens - uncached_before
        episode.transcript = "".join(self.transcript)
        _score(episode, self.scenario)
        return episode

    @property
    def event_pending(self) -> bool:
        return self.episode.event_at_token is not None and self.episode.delivered_at_token is None

    def deliver_now(self) -> None:
        if self.delivery is Delivery.INJECT:
            self.episode.delivered_at_token = self.episode.completion_tokens
            self.backend.inject(self.scenario.event_block)
            self.turn.append(self.scenario.event_block)
            self.feed(self.scenario.event_block)
        else:
            self.deliver_as_new_turn()

    def deliver_as_new_turn(self) -> None:
        self.episode.delivered_at_token = self.episode.completion_tokens
        note = INTERRUPTED_NOTE if self.delivery is Delivery.CANCEL_RESEND else ""
        self.messages.append({"role": "assistant", "content": "".join(self.turn)})
        self.messages.append({"role": "user", "content": self.scenario.event_block + note})
        self.turn.clear()
        self.backend.begin(self.messages)
        self.episode.llm_calls += 1
        self.transcript.append(f"\n[user] {self.scenario.event_block}")

    def feed(self, text: str) -> None:
        """Parse generated or injected text and update the guide."""
        self.transcript.append(text)
        for event in self.processor.process_chunk(text):
            if isinstance(event, BlockStartEvent):
                self.inside_block, self.block_started_at = True, self.line_started_at
            elif isinstance(event, BlockErrorEvent):
                self.inside_block = False
                self.episode.malformed_blocks += 1
            elif isinstance(event, BlockEndEvent):
                self.inside_block = False
                if event.block_type == STEP:
                    self.close_step(str(event.metadata["id"]), str(event.content["raw_content"]))
        if text.endswith("\n"):
            self.line_started_at = self.episode.completion_tokens

    def close_step(self, step_id: str, content: str) -> None:
        self.steps_closed += 1
        self.episode.guide[step_id] = content
        if self.episode.event_at_token is not None:
            # A step rewritten after the event makes its previous version wasted work.
            self.episode.wasted_tokens += self.step_tokens.get(step_id, 0)
            self.step_tokens[step_id] = self.episode.completion_tokens - self.block_started_at


def _score(episode: Episode, scenario: Scenario) -> None:
    """Compliant: every step exists, and those after the event follow it."""
    all_ids = [f"s{n}" for n in range(1, scenario.steps + 1)]
    later = [episode.guide.get(step_id, "") for step_id in all_ids[scenario.event_after_step :]]
    forbidden = re.compile(scenario.forbidden, re.IGNORECASE)
    required = re.compile(scenario.required, re.IGNORECASE)
    episode.steps_present = sum(step_id in episode.guide for step_id in all_ids)
    episode.compliant = (
        episode.delivered_at_token is not None
        and episode.steps_present == scenario.steps
        and not any(forbidden.search(step) for step in later)
        and any(required.search(step) for step in later)
    )
