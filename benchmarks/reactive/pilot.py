"""Injection pilot: does a model use an event delivered into its own output stream?

uv run --with llama-cpp-python python -m benchmarks.reactive.pilot --model path/to/model.gguf
    uv run --with pie-client python -m benchmarks.reactive.pilot --backend pie --model qwen3.5-0.8b
    uv run python -m benchmarks.reactive.pilot --summarize runs/reactive/pilot.jsonl
"""

from __future__ import annotations

import argparse
import importlib
import json
from dataclasses import asdict, fields
from pathlib import Path
from statistics import median

from benchmarks.reactive.clock import COSTS
from benchmarks.reactive.steering import SCENARIOS, Delivery, Episode, run_episode


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--backend", choices=["llamacpp", "pie"], default="llamacpp")
    parser.add_argument("--model", help="llamacpp: path to a GGUF model. pie: label of the model `pie serve` runs")
    parser.add_argument("--summarize", type=Path, help="Print the summary of an existing run and exit")
    parser.add_argument("--reps", type=int, default=3)
    parser.add_argument("--cost", choices=sorted(COSTS), default="local", help="Cost model for virtual time")
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--max-tokens", type=int, default=1500)
    parser.add_argument("--out", type=Path, default=Path("runs/reactive/pilot.jsonl"))
    args = parser.parse_args()
    if args.summarize:
        print_summary(load_episodes(args.summarize))
        return
    if not args.model:
        parser.error("--model is required to run episodes")

    # Imported here so that each backend's package is only needed when that backend is used.
    if args.backend == "pie":
        backend = importlib.import_module("benchmarks.reactive.pie").PieBackend()
    else:
        llamacpp = importlib.import_module("benchmarks.reactive.llamacpp")
        backend = llamacpp.LlamaCppBackend(args.model, temperature=args.temperature)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    episodes: list[Episode] = []
    with args.out.open("a") as out:
        for rep in range(args.reps):
            for scenario in SCENARIOS:
                for delivery in Delivery:
                    backend.set_seed(rep)
                    episode = run_episode(
                        backend, scenario, delivery, max_tokens=args.max_tokens, cost=COSTS[args.cost]
                    )
                    episodes.append(episode)
                    record = {"backend": args.backend, "model": Path(args.model).name, "seed": rep, **asdict(episode)}
                    out.write(json.dumps(record) + "\n")
                    out.flush()
                    print(f"rep={rep} {scenario.name:<10} {delivery.value:<14} compliant={episode.compliant}")
    if args.backend == "pie":
        backend.close()
    print_summary(episodes)


def load_episodes(path: Path) -> list[Episode]:
    names = {f.name for f in fields(Episode)}
    with path.open() as lines:
        return [Episode(**{k: v for k, v in json.loads(line).items() if k in names}) for line in lines]


def print_summary(episodes: list[Episode]) -> None:
    columns = ("delivery", "n", "compliant", "latency", "wasted", "completion", "uncached", "calls", "seconds")
    print("\n" + "  ".join(f"{name:>13}" for name in columns))
    for delivery in Delivery:
        rows = [episode for episode in episodes if episode.delivery == delivery.value]
        if not rows:
            continue
        latencies = [e.reaction_latency_tokens for e in rows if e.reaction_latency_tokens is not None]
        cells = (
            delivery.value,
            len(rows),
            f"{sum(e.compliant for e in rows)}/{len(rows)}",
            median(latencies) if latencies else "-",
            median(e.wasted_tokens for e in rows),
            median(e.completion_tokens for e in rows),
            median(e.uncached_prompt_tokens for e in rows),
            median(e.llm_calls for e in rows),
            round(median(e.virtual_time_s for e in rows), 1),
        )
        print("  ".join(f"{cell!s:>13}" for cell in cells))
    print("\nlatency, wasted, completion and uncached are median token counts per episode; seconds is virtual time.")


if __name__ == "__main__":
    main()
