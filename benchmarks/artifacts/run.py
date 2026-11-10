"""Run the artifact benchmark matrix, or summarise a previous run.

    uv run --with llama-cpp-python python -m benchmarks.artifacts.run --gguf path/to/model.gguf
    uv run --with openai python -m benchmarks.artifacts.run --base-url http://localhost:1234/v1 --model my-model
    uv run python -m benchmarks.artifacts.run --summarize runs/artifacts/pilot.jsonl

Episodes are appended to a JSONL file as they finish. Re-running the same
command skips the episodes already in the file, so an interrupted sweep resumes.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from benchmarks.artifacts.arms import build_arms
from benchmarks.artifacts.backends import LlamaCppBackend, OpenAICompatibleBackend
from benchmarks.artifacts.episode import run_episode
from benchmarks.artifacts.summary import print_summary
from benchmarks.artifacts.tasks import TASKS, TASKS_BY_NAME

if TYPE_CHECKING:
    from benchmarks.artifacts.backends import ChatBackend

DEFAULT_OUT = Path("runs/artifacts/pilot.jsonl")
Key = tuple[str, str, str, int]


def load_records(path: Path) -> list[dict[str, Any]]:
    """Read episode records, ignoring a torn last line from an interrupted run."""
    records: list[dict[str, Any]] = []
    if not path.exists():
        return records
    for line in path.read_text().splitlines():
        try:
            records.append(json.loads(line))
        except ValueError:
            continue
    return records


def episode_key(record: dict[str, Any]) -> Key:
    """What identifies an episode within a run file."""
    return (str(record["model"]), str(record["arm"]), str(record["task"]), int(record["seed"]))


def run_matrix(
    backend: ChatBackend,
    *,
    arms: list[str],
    tasks: list[str],
    seeds: int,
    out: Path,
    max_tokens: int,
    temperature: float,
) -> None:
    """Run every (seed, task, arm) episode not already in ``out``, interleaved so partial runs stay balanced."""
    all_arms = build_arms()
    done = {episode_key(record) for record in load_records(out) if record.get("error") is None}
    out.parent.mkdir(parents=True, exist_ok=True)
    existing = out.read_text() if out.exists() else ""
    torn = bool(existing) and not existing.endswith("\n")
    with out.open("a") as sink:
        if torn:
            # An interrupted run left a partial line; start the next record on its own line
            sink.write("\n")
        for seed in range(seeds):
            for task_name in tasks:
                for arm_name in arms:
                    if (backend.model, arm_name, task_name, seed) in done:
                        continue
                    episode = run_episode(
                        backend,
                        all_arms[arm_name],
                        TASKS_BY_NAME[task_name],
                        seed=seed,
                        max_tokens=max_tokens,
                        temperature=temperature,
                    )
                    sink.write(json.dumps(episode.to_record()) + "\n")
                    sink.flush()
                    print(
                        f"seed={seed} {task_name:<15} {arm_name:<20} ok={episode.score:.0f} "
                        f"well_formed={episode.well_formed} tokens={episode.completion_tokens} "
                        f"{episode.tokens_per_s:.0f} tok/s {episode.error or ''}"
                    )


def main() -> None:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--gguf", help="Path to a GGUF model, run in-process with llama-cpp-python")
    parser.add_argument("--base-url", help="Base URL of an OpenAI-compatible server")
    parser.add_argument("--model", help="Model name on the OpenAI-compatible server")
    parser.add_argument("--grammar-field", default="grammar", help="Request field carrying the GBNF grammar")
    parser.add_argument("--arms", default=",".join(build_arms()), help="Comma-separated arm names")
    parser.add_argument("--tasks", default=",".join(task.name for task in TASKS), help="Comma-separated task names")
    parser.add_argument("--seeds", type=int, default=3)
    parser.add_argument("--max-tokens", type=int, default=1200)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--summarize", type=Path, help="Print the summary of an existing run and exit")
    args = parser.parse_args()

    if args.summarize:
        print_summary(load_records(args.summarize))
        return
    if args.gguf:
        backend: ChatBackend = LlamaCppBackend(args.gguf)
    elif args.base_url and args.model:
        backend = OpenAICompatibleBackend(args.base_url, args.model, grammar_field=args.grammar_field)
    else:
        parser.error("give --gguf, or --base-url with --model, or --summarize")

    run_matrix(
        backend,
        arms=args.arms.split(","),
        tasks=args.tasks.split(","),
        seeds=args.seeds,
        out=args.out,
        max_tokens=args.max_tokens,
        temperature=args.temperature,
    )
    print_summary(load_records(args.out))


if __name__ == "__main__":
    main()
