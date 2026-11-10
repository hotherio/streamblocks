"""The loop every reactive scenario shares: generate, parse blocks, deliver events, keep the clock."""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from benchmarks.reactive.clock import VirtualClock
from hother.streamblocks import DelimiterPreambleSyntax, Registry, StreamBlockProcessor
from hother.streamblocks.core.processor import ProcessorConfig
from hother.streamblocks.core.types import BlockEndEvent, BlockErrorEvent, BlockStartEvent

if TYPE_CHECKING:
    from benchmarks.reactive.backend import Backend, Message
    from benchmarks.reactive.clock import CostModel


class Delivery(StrEnum):
    """How an event reaches the model."""

    TURN_BOUNDARY = "turn_boundary"  # as a new user turn, after the model finished
    CANCEL_RESEND = "cancel_resend"  # stop the model, send a new user turn
    INJECT = "inject"  # appended to the model's own turn, generation continues


@dataclass
class Record:
    """What every scenario measures. Field names follow the shared benchmark episode record."""

    task: str
    delivery: str
    compliant: bool = False
    completion_tokens: int = 0
    llm_calls: int = 1
    resent_prompt_tokens: int = 0
    uncached_prompt_tokens: int = 0
    malformed_blocks: int = 0
    virtual_time_s: float = 0.0
    wall_time_s: float = 0.0
    transcript: str = ""


class Run[R: Record]:
    """One episode. A scenario subclasses this and fills in the four hooks."""

    # Without this, a model cut off mid-answer treats the event as a new request and starts over.
    interrupted_note = "Your output was interrupted by this event. Continue where you stopped."

    def __init__(
        self,
        backend: Backend,
        record: R,
        delivery: Delivery,
        system: str,
        task: str,
        cost: CostModel,
        registry: Registry | None = None,
    ) -> None:
        self.backend = backend
        self.record = record
        self.delivery = delivery
        self.clock = VirtualClock(cost)
        self.processor = StreamBlockProcessor(
            registry or Registry(syntax=DelimiterPreambleSyntax()),
            ProcessorConfig(emit_text_deltas=False, emit_original_events=False, auto_detect_adapter=False),
        )
        self.messages: list[Message] = [{"role": "system", "content": system}, {"role": "user", "content": task}]
        self.turn: list[str] = []
        self.transcript: list[str] = []
        self.line_started_at = 0  # completion tokens when the current line began
        self.block_started_at = 0
        self.inside_block = False

    def due(self, *, idle: bool) -> str | None:
        """Event text to deliver now, if any. `idle` means the model ended its turn and is waiting."""
        raise NotImplementedError

    def delivered(self) -> None:
        """The text last returned by `due` is about to reach the model."""

    def block_closed(self, event: BlockEndEvent) -> None:
        """The model (or an injected event) closed a block."""

    def score(self) -> None:
        raise NotImplementedError

    def run(self, max_tokens: int) -> R:
        record, backend = self.record, self.backend
        prompt_before, uncached_before = backend.prompt_tokens, backend.uncached_prompt_tokens
        started = time.perf_counter()
        self.begin()

        while record.completion_tokens < max_tokens:
            piece = backend.next_piece()
            if piece is None:
                self.feed("\n")
                event = self.due(idle=True)
                if event is None:
                    break
                self.deliver_as_new_turn(event)
                continue
            record.completion_tokens += 1
            self.clock.generated()
            self.turn.append(piece)
            self.feed(piece)
            event = self.due(idle=False)
            at_boundary = piece.endswith("\n") and not self.inside_block
            if event and at_boundary and self.delivery is not Delivery.TURN_BOUNDARY:
                self.deliver(event)

        record.malformed_blocks += sum(isinstance(e, BlockErrorEvent) for e in self.processor.finalize())
        record.resent_prompt_tokens = backend.prompt_tokens - prompt_before
        record.uncached_prompt_tokens = backend.uncached_prompt_tokens - uncached_before
        record.transcript = "".join(self.transcript)
        record.virtual_time_s = round(self.clock.now, 3)
        record.wall_time_s = round(time.perf_counter() - started, 3)
        self.score()
        return record

    def begin(self) -> None:
        before = self.backend.uncached_prompt_tokens
        self.backend.begin(self.messages)
        self.clock.call(self.backend.uncached_prompt_tokens - before)

    def deliver(self, event: str) -> None:
        if self.delivery is not Delivery.INJECT:
            self.deliver_as_new_turn(event)
            return
        self.delivered()
        self.clock.prefill(self.backend.inject(event))
        self.turn.append(event)
        self.feed(event)

    def deliver_as_new_turn(self, event: str) -> None:
        self.delivered()
        note = self.interrupted_note if self.delivery is Delivery.CANCEL_RESEND else ""
        self.messages.append({"role": "assistant", "content": "".join(self.turn)})
        self.messages.append({"role": "user", "content": event + note})
        self.turn.clear()
        self.begin()
        self.record.llm_calls += 1
        self.transcript.append(f"\n[user] {event}")

    def feed(self, text: str) -> None:
        """Parse generated or injected text."""
        self.transcript.append(text)
        for event in self.processor.process_chunk(text):
            if isinstance(event, BlockStartEvent):
                self.inside_block, self.block_started_at = True, self.line_started_at
            elif isinstance(event, BlockErrorEvent):
                self.inside_block = False
                self.record.malformed_blocks += 1
            elif isinstance(event, BlockEndEvent):
                self.inside_block = False
                self.block_closed(event)
        if text.endswith("\n"):
            self.line_started_at = self.record.completion_tokens
