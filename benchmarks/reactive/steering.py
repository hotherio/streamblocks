"""Mid-turn steering: a correction arrives while the model is writing a guide.

The model writes steps as blocks. Once `event_after_step` steps are closed, an event
block becomes available and is delivered one of three ways (`Delivery`). Later step
blocks override earlier ones with the same id, and a regex check scores the final guide.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from benchmarks.reactive.clock import COSTS, CostModel
from benchmarks.reactive.loop import Delivery, Record, Run

if TYPE_CHECKING:
    from benchmarks.reactive.backend import Backend
    from hother.streamblocks.core.types import BlockEndEvent

STEP = "step"
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
class Episode(Record):
    steps_present: int = 0
    event_at_token: int | None = None
    delivered_at_token: int | None = None
    reaction_latency_tokens: int | None = None
    wasted_tokens: int = 0
    guide: dict[str, str] = field(default_factory=dict[str, str])


def run_episode(
    backend: Backend,
    scenario: Scenario,
    delivery: Delivery,
    *,
    max_tokens: int = 1500,
    cost: CostModel = COSTS["local"],
) -> Episode:
    return _Run(backend, scenario, delivery, cost).run(max_tokens)


class _Run(Run[Episode]):
    interrupted_note = INTERRUPTED_NOTE

    def __init__(self, backend: Backend, scenario: Scenario, delivery: Delivery, cost: CostModel) -> None:
        episode = Episode(task=scenario.name, delivery=delivery.value)
        super().__init__(backend, episode, delivery, SYSTEM_PROMPT, scenario.task, cost)
        self.scenario = scenario
        self.step_tokens: dict[str, int] = {}  # tokens of the latest version of each step written after the event
        self.steps_closed = 0

    def due(self, *, idle: bool) -> str | None:
        episode = self.record
        if not idle and episode.event_at_token is None and self.steps_closed >= self.scenario.event_after_step:
            episode.event_at_token = episode.completion_tokens
        pending = episode.event_at_token is not None and episode.delivered_at_token is None
        return self.scenario.event_block if pending else None

    def delivered(self) -> None:
        self.record.delivered_at_token = self.record.completion_tokens

    def block_closed(self, event: BlockEndEvent) -> None:
        if event.block_type != STEP:
            return
        episode, step_id = self.record, str(event.metadata["id"])
        self.steps_closed += 1
        episode.guide[step_id] = str(event.content["raw_content"])
        if episode.event_at_token is not None:
            # A step rewritten after the event makes its previous version wasted work.
            episode.wasted_tokens += self.step_tokens.get(step_id, 0)
            self.step_tokens[step_id] = episode.completion_tokens - self.block_started_at

    def score(self) -> None:
        """Compliant: every step exists, and those after the event follow it."""
        episode, scenario = self.record, self.scenario
        if episode.event_at_token is not None and episode.delivered_at_token is not None:
            episode.reaction_latency_tokens = episode.delivered_at_token - episode.event_at_token
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
