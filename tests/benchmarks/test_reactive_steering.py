"""Steering scenario logic, driven by a scripted backend (no model)."""

from benchmarks.reactive.backend import ScriptedBackend
from benchmarks.reactive.clock import COSTS
from benchmarks.reactive.steering import SCENARIOS, Delivery, run_episode

DATABASE = SCENARIOS[0]


def _steps(numbers: range, database: str) -> list[str]:
    return [piece for n in numbers for piece in (f"!!s{n}:step\n", f"Step {n} uses {database}.\n", "!!end\n")]


OLD_PLAN = _steps(range(1, 7), "SQLite")
NEW_TAIL = _steps(range(3, 7), "PostgreSQL")


def test_inject_delivers_inside_the_turn_with_one_call() -> None:
    backend = ScriptedBackend([OLD_PLAN], after_inject=NEW_TAIL)
    episode = run_episode(backend, DATABASE, Delivery.INJECT)

    assert backend.injected == [DATABASE.event_block]
    assert episode.compliant
    assert (episode.llm_calls, episode.reaction_latency_tokens, episode.wasted_tokens) == (1, 0, 0)
    assert "!!e1:event" in episode.transcript


def test_cancel_resend_stops_the_turn_and_starts_a_new_one() -> None:
    backend = ScriptedBackend([OLD_PLAN, NEW_TAIL])
    episode = run_episode(backend, DATABASE, Delivery.CANCEL_RESEND)

    assert episode.compliant
    assert (episode.llm_calls, episode.reaction_latency_tokens, episode.wasted_tokens) == (2, 0, 0)
    assert episode.completion_tokens == len(OLD_PLAN[:6]) + len(NEW_TAIL)


def test_turn_boundary_wastes_the_steps_written_after_the_event() -> None:
    backend = ScriptedBackend([OLD_PLAN, NEW_TAIL])
    episode = run_episode(backend, DATABASE, Delivery.TURN_BOUNDARY)

    assert episode.compliant
    assert episode.llm_calls == 2
    assert episode.reaction_latency_tokens == len(OLD_PLAN[6:])
    assert episode.wasted_tokens == len(OLD_PLAN[6:])


def test_ignoring_the_event_is_not_compliant() -> None:
    backend = ScriptedBackend([OLD_PLAN], after_inject=OLD_PLAN[6:])
    episode = run_episode(backend, DATABASE, Delivery.INJECT)

    assert not episode.compliant
    assert episode.steps_present == DATABASE.steps


def test_event_waits_for_a_line_boundary_outside_any_block() -> None:
    glued = [*OLD_PLAN[:5], "!!end\n!!s3:step\n", *OLD_PLAN[7:]]
    backend = ScriptedBackend([glued], after_inject=_steps(range(4, 7), "PostgreSQL"))
    episode = run_episode(backend, DATABASE, Delivery.INJECT)

    assert episode.reaction_latency_tokens == 2  # the rest of step 3, already begun
    assert not episode.compliant  # step 3 was finished under the old plan


def test_virtual_time_is_replayable_and_orders_the_deliveries() -> None:
    def seconds(delivery: Delivery) -> float:
        backend = ScriptedBackend([OLD_PLAN, NEW_TAIL], after_inject=NEW_TAIL)
        return run_episode(backend, DATABASE, delivery, cost=COSTS["hosted"]).virtual_time_s

    assert seconds(Delivery.INJECT) == seconds(Delivery.INJECT)
    assert seconds(Delivery.INJECT) < seconds(Delivery.CANCEL_RESEND) < seconds(Delivery.TURN_BOUNDARY)
