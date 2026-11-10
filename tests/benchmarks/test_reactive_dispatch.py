"""Dispatch scenario logic, driven by a scripted backend (no model)."""

from benchmarks.reactive.backend import ScriptedBackend
from benchmarks.reactive.clock import CostModel
from benchmarks.reactive.dispatch import Repair, Scenario, WorldEvent, run_episode
from benchmarks.reactive.loop import Delivery

ONE_PIECE_PER_SECOND = CostModel(decode_tps=1, prefill_tps=float("inf"), call_overhead_s=0)
PIECES_PER_BLOCK = 3
CY_OFFLINE = WorldEvent(7.0, "cy went offline.", offline="cy")  # while J3 -> cy is being written
SCENARIO = Scenario("test", ("ana", "ben", "cy"), (CY_OFFLINE,), jobs=6)
LATE = Scenario("late", ("ana", "ben", "cy"), (WorldEvent(100.0, "cy went offline.", offline="cy"),), jobs=6)


def _assign(pairs: dict[int, str]) -> list[str]:
    return [
        piece for job, worker in pairs.items() for piece in (f"!!a{job}:assign\n", f"J{job} -> {worker}\n", "!!end\n")
    ]


ROUND_ROBIN = _assign({1: "ana", 2: "ben", 3: "cy", 4: "ana", 5: "ben", 6: "cy"})
WITHOUT_CY = _assign({3: "ana", 4: "ben", 5: "ana", 6: "ben"})
REPAIR = _assign({3: "ana", 6: "ben"})


def _run(backend: ScriptedBackend, delivery: Delivery, scenario: Scenario = SCENARIO):
    return run_episode(backend, scenario, delivery, cost=ONE_PIECE_PER_SECOND)


def test_inject_leaves_only_the_action_already_in_flight_stale() -> None:
    episode = _run(ScriptedBackend([ROUND_ROBIN], after_inject=WITHOUT_CY), Delivery.INJECT)

    assert episode.compliant
    assert (episode.stale_actions, episode.llm_calls) == (1, 1)
    assert (episode.reaction_latency_tokens, episode.reaction_latency_s) == (2, 2.0)
    assert episode.assignments["J3"] == "ana"


def test_turn_boundary_executes_every_stale_action_before_hearing_of_the_event() -> None:
    episode = _run(ScriptedBackend([ROUND_ROBIN, REPAIR]), Delivery.TURN_BOUNDARY)

    assert episode.compliant
    assert (episode.stale_actions, episode.llm_calls) == (2, 2)
    assert episode.reaction_latency_tokens == len(ROUND_ROBIN) - CY_OFFLINE.at_s


def test_ignoring_the_event_is_not_compliant() -> None:
    episode = _run(ScriptedBackend([ROUND_ROBIN], after_inject=ROUND_ROBIN[3 * PIECES_PER_BLOCK :]), Delivery.INJECT)

    assert not episode.compliant
    assert (episode.stale_actions, episode.jobs_placed) == (2, 4)


def test_an_idle_model_is_woken_when_the_event_happens() -> None:
    episode = _run(ScriptedBackend([ROUND_ROBIN, REPAIR]), Delivery.INJECT, LATE)

    assert episode.compliant
    assert (episode.stale_actions, episode.llm_calls, episode.reaction_latency_s) == (0, 2, 0.0)
    assert episode.virtual_time_s == LATE.events[0].at_s + len(REPAIR)


def test_a_named_event_lists_the_jobs_the_offline_worker_had() -> None:
    backend = ScriptedBackend([ROUND_ROBIN], after_inject=WITHOUT_CY)
    run_episode(backend, SCENARIO, Delivery.INJECT, cost=ONE_PIECE_PER_SECOND, repair=Repair.NAMED)

    assert backend.injected == [
        "!!e1:event\ncy went offline.\nAssign these jobs again, they were given to cy: J3.\n!!end\n"
    ]


def test_a_state_event_lists_every_current_assignment() -> None:
    backend = ScriptedBackend([ROUND_ROBIN], after_inject=WITHOUT_CY)
    run_episode(backend, SCENARIO, Delivery.INJECT, cost=ONE_PIECE_PER_SECOND, repair=Repair.STATE)

    assert backend.injected[0].splitlines()[2:6] == ["Current assignments:", "J1 -> ana", "J2 -> ben", "J3 -> cy"]
