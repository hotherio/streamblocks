"""Reactive pilot: does a model use an event delivered into its own output stream?

uv run --with llama-cpp-python python -m benchmarks.reactive.pilot --model path/to/model.gguf
    uv run --with llama-cpp-python python -m benchmarks.reactive.pilot --scenario dispatch --model path/to/model.gguf
    uv run --with pie-client python -m benchmarks.reactive.pilot --backend pie --model qwen3.5-4b
    uv run python -m benchmarks.reactive.pilot --summarize runs/reactive/steering.jsonl
"""

from __future__ import annotations

import argparse
import importlib
import json
from dataclasses import asdict, fields
from pathlib import Path
from statistics import median
from typing import TYPE_CHECKING, Any

from benchmarks.reactive import dispatch, steering
from benchmarks.reactive.clock import COSTS
from benchmarks.reactive.loop import Delivery

if TYPE_CHECKING:
    from benchmarks.reactive.loop import Record

MODULES = {"steering": steering, "dispatch": dispatch}
# Scenario-specific summary columns: label -> episode field (median over episodes).
EXTRA_COLUMNS = {
    "steering": {"latency": "reaction_latency_tokens", "wasted": "wasted_tokens"},
    "dispatch": {"latency": "reaction_latency_tokens", "stale": "stale_actions"},
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scenario", choices=sorted(MODULES), default="steering")
    parser.add_argument("--backend", choices=["llamacpp", "pie"], default="llamacpp")
    parser.add_argument("--model", help="llamacpp: path to a GGUF model. pie: label of the model `pie serve` runs")
    parser.add_argument("--summarize", type=Path, help="Print the summary of an existing run and exit")
    parser.add_argument("--reps", type=int, default=3)
    parser.add_argument("--cost", choices=sorted(COSTS), default="local", help="Cost model for virtual time")
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--max-tokens", type=int, default=1500)
    parser.add_argument("--out", type=Path, help="Default: runs/reactive/<scenario>.jsonl")
    args = parser.parse_args()
    if args.summarize:
        print_summary(*load_episodes(args.summarize))
        return
    if not args.model:
        parser.error("--model is required to run episodes")

    # Imported here so that each backend's package is only needed when that backend is used.
    if args.backend == "pie":
        backend = importlib.import_module("benchmarks.reactive.pie").PieBackend()
    else:
        llamacpp = importlib.import_module("benchmarks.reactive.llamacpp")
        backend = llamacpp.LlamaCppBackend(args.model, temperature=args.temperature)
    module = MODULES[args.scenario]
    out_path = args.out or Path(f"runs/reactive/{args.scenario}.jsonl")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    episodes: list[Record] = []
    tags = {"scenario": args.scenario, "backend": args.backend, "model": Path(args.model).name, "cost": args.cost}
    with out_path.open("a") as out:
        for rep in range(args.reps):
            for scenario in module.SCENARIOS:
                for delivery in Delivery:
                    backend.set_seed(rep)
                    episode = module.run_episode(
                        backend, scenario, delivery, max_tokens=args.max_tokens, cost=COSTS[args.cost]
                    )
                    episodes.append(episode)
                    out.write(json.dumps({**tags, "seed": rep, **asdict(episode)}) + "\n")
                    out.flush()
                    print(f"rep={rep} {scenario.name:<20} {delivery.value:<14} compliant={episode.compliant}")
    if args.backend == "pie":
        backend.close()
    print_summary(args.scenario, episodes)


def load_episodes(path: Path) -> tuple[str, list[Record]]:
    """Read a run back. Runs made before scenarios were tagged are steering runs."""
    with path.open() as lines:
        records: list[dict[str, Any]] = [json.loads(line) for line in lines]
    scenario = records[0].get("scenario", "steering")
    episode_type = MODULES[scenario].Episode
    names = {f.name for f in fields(episode_type)}
    return scenario, [episode_type(**{k: v for k, v in record.items() if k in names}) for record in records]


def print_summary(scenario: str, episodes: list[Record]) -> None:
    extra = EXTRA_COLUMNS[scenario]
    columns = ("delivery", "n", "compliant", *extra, "completion", "uncached", "calls", "seconds")
    print("\n" + "  ".join(f"{name:>13}" for name in columns))
    for delivery in Delivery:
        rows = [episode for episode in episodes if episode.delivery == delivery.value]
        if not rows:
            continue
        cells = (
            delivery.value,
            len(rows),
            f"{sum(e.compliant for e in rows)}/{len(rows)}",
            *(_median(getattr(e, name) for e in rows) for name in extra.values()),
            median(e.completion_tokens for e in rows),
            median(e.uncached_prompt_tokens for e in rows),
            median(e.llm_calls for e in rows),
            round(median(e.virtual_time_s for e in rows), 1),
        )
        print("  ".join(f"{cell!s:>13}" for cell in cells))
    print("\nAll but n, compliant and seconds are medians per episode; latency, completion and uncached count tokens.")


def _median(values: Any) -> float | str:
    present = [value for value in values if value is not None]
    return round(median(present), 1) if present else "-"


if __name__ == "__main__":
    main()
