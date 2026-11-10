"""Live dispatch: the world changes on the clock while the model assigns jobs to workers.

An assignment takes effect when its block closes. One made after an event it contradicts is a
stale action: it cannot be taken back, only corrected by a later assignment of the same job.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from statistics import mean
from typing import TYPE_CHECKING

from benchmarks.reactive.clock import COSTS, CostModel
from benchmarks.reactive.loop import Delivery, Record, Run

if TYPE_CHECKING:
    from benchmarks.reactive.backend import Backend
    from hother.streamblocks.core.types import BlockEndEvent

ASSIGN = "assign"
_ASSIGNMENT = re.compile(r"\b(J\d+)\s*->\s*(\w+)", re.IGNORECASE)
SYSTEM_PROMPT = """You are a dispatcher. You assign jobs to workers with assign blocks, and write nothing outside \
blocks. Each block is exactly:

!!a<N>:assign
<job> -> <worker>
!!end

Every block ends with a line containing only !!end, before the next block starts. An assignment takes \
effect as soon as its block ends. Example:

!!a1:assign
J1 -> kim
!!end
!!a2:assign
J2 -> lou
!!end

The environment can send you an event block at any moment, even in the middle of your own output:

!!e<N>:event
<what changed>
!!end

Never write an event block yourself. When one appears, obey it at once. Never assign a job to a worker \
who is offline, and never assign a cancelled job. If a job is assigned to a worker who is now offline, \
assign it again to another worker with a new block. Do not repeat assignments that are still valid. \
Stop when every job that is not cancelled has a worker who is online."""


@dataclass(frozen=True)
class WorldEvent:
    at_s: float
    text: str
    offline: str = ""
    cancelled: str = ""

    def contradicts(self, job: str, worker: str) -> bool:
        return worker == self.offline or job == self.cancelled


@dataclass(frozen=True)
class Scenario:
    name: str
    workers: tuple[str, ...]
    events: tuple[WorldEvent, ...]
    jobs: int = 10

    @property
    def task(self) -> str:
        return (
            f"Assign jobs J1 to J{self.jobs}, in order, one block per job, to these workers: "
            f"{', '.join(self.workers)}. Spread the jobs evenly between them."
        )

    def event_block(self, index: int) -> str:
        return f"!!e{index + 1}:event\n{self.events[index].text}\n!!end\n"


def _offline(at_s: float, worker: str) -> WorldEvent:
    return WorldEvent(at_s, f"{worker} went offline and can no longer take any job.", offline=worker)


def _cancelled(at_s: float, job: str) -> WorldEvent:
    return WorldEvent(at_s, f"{job} is cancelled.", cancelled=job)


TRIO = ("ana", "ben", "cy")
SCENARIOS = [
    Scenario("offline_early", TRIO, (_offline(2.0, "cy"),)),
    Scenario("offline_late", TRIO, (_offline(3.5, "ben"),)),
    Scenario("cancel", TRIO, (_cancelled(1.5, "J8"),)),
    Scenario("offline_then_cancel", TRIO, (_offline(1.0, "cy"), _cancelled(2.5, "J9"))),
    Scenario("two_offline", (*TRIO, "dee"), (_offline(1.0, "dee"), _offline(3.0, "ana"))),
]


@dataclass
class Episode(Record):
    stale_actions: int = 0
    jobs_placed: int = 0  # live jobs whose final worker is online
    events_delivered: int = 0
    reaction_latency_tokens: float | None = None  # mean over events, availability to delivery
    reaction_latency_s: float | None = None
    assignments: dict[str, str] = field(default_factory=dict[str, str])


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
    def __init__(self, backend: Backend, scenario: Scenario, delivery: Delivery, cost: CostModel) -> None:
        episode = Episode(task=scenario.name, delivery=delivery.value)
        super().__init__(backend, episode, delivery, SYSTEM_PROMPT, scenario.task, cost)
        self.scenario = scenario
        self.available_at: dict[int, int] = {}  # event index -> completion tokens when it happened
        self.ready: list[int] = []
        self.latency_tokens: list[int] = []
        self.latency_s: list[float] = []

    def due(self, *, idle: bool) -> str | None:
        events, first = self.scenario.events, self.record.events_delivered
        if first == len(events):
            return None
        if idle:  # nothing to do until the next event: time passes
            self.clock.now = max(self.clock.now, events[first].at_s)
        self.ready = [i for i in range(first, len(events)) if events[i].at_s <= self.clock.now]
        for index in self.ready:
            self.available_at.setdefault(index, self.record.completion_tokens)
        return "".join(self.scenario.event_block(index) for index in self.ready) or None

    def delivered(self) -> None:
        for index in self.ready:
            self.latency_tokens.append(self.record.completion_tokens - self.available_at[index])
            self.latency_s.append(self.clock.now - self.scenario.events[index].at_s)
        self.record.events_delivered += len(self.ready)

    def block_closed(self, event: BlockEndEvent) -> None:
        if event.block_type != ASSIGN:
            return
        match = _ASSIGNMENT.search(str(event.content["raw_content"]))
        if match is None:
            self.record.malformed_blocks += 1
            return
        job, worker = match[1].upper(), match[2].lower()
        self.record.assignments[job] = worker
        happened = [e for e in self.scenario.events if e.at_s <= self.clock.now]
        self.record.stale_actions += any(e.contradicts(job, worker) for e in happened)

    def score(self) -> None:
        """Compliant: every event was delivered and every live job ends on an online worker."""
        episode, scenario = self.record, self.scenario
        online = set(scenario.workers) - {e.offline for e in scenario.events}
        cancelled = {e.cancelled for e in scenario.events}
        live = [job for job in (f"J{n}" for n in range(1, scenario.jobs + 1)) if job not in cancelled]
        episode.jobs_placed = sum(episode.assignments.get(job) in online for job in live)
        episode.compliant = episode.events_delivered == len(scenario.events) and episode.jobs_placed == len(live)
        if self.latency_tokens:
            episode.reaction_latency_tokens = mean(self.latency_tokens)
            episode.reaction_latency_s = round(mean(self.latency_s), 3)
