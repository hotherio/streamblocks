"""Summarise episode records: rates with bootstrap intervals, medians, failure codes."""

from __future__ import annotations

from collections import Counter, defaultdict
from random import Random
from statistics import median
from typing import Any

_BOOTSTRAP_RESAMPLES = 2000
_BOOTSTRAP_SEED = 0
_LOWER_QUANTILE = 0.025
_UPPER_QUANTILE = 0.975
_PERCENT = 100


def rate_interval(values: list[float]) -> tuple[float, float, float]:
    """Mean of ``values`` with a 95% percentile-bootstrap interval."""
    if not values:
        return (0.0, 0.0, 0.0)
    rng = Random(_BOOTSTRAP_SEED)
    size = len(values)
    means = sorted(sum(rng.choices(values, k=size)) / size for _ in range(_BOOTSTRAP_RESAMPLES))
    low = means[int(_LOWER_QUANTILE * _BOOTSTRAP_RESAMPLES)]
    high = means[min(int(_UPPER_QUANTILE * _BOOTSTRAP_RESAMPLES), _BOOTSTRAP_RESAMPLES - 1)]
    return (sum(values) / size, low, high)


def summarize(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One row per (model, arm), in first-seen order."""
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        if record.get("error") is None:
            groups[(str(record["model"]), str(record["arm"]))].append(record)

    rows: list[dict[str, Any]] = []
    for (model, arm), episodes in groups.items():
        codes: Counter[str] = Counter()
        for episode in episodes:
            codes.update(episode["malformed_by_code"])
        first = [e["first_artifact_piece"] / e["completion_tokens"] for e in episodes if e["first_artifact_piece"]]
        rows.append(
            {
                "model": model,
                "arm": arm,
                "n": len(episodes),
                "pass": rate_interval([float(e["score"]) for e in episodes]),
                "well_formed": rate_interval([float(e["well_formed"]) for e in episodes]),
                "tokens": median(e["completion_tokens"] for e in episodes),
                "tokens_per_s": median(e["tokens_per_s"] for e in episodes),
                "first_artifact": median(first) if first else None,
                "truncated": sum(bool(e["truncated"]) for e in episodes),
                "codes": dict(codes),
            }
        )
    return rows


def _percent(rate: tuple[float, float, float]) -> str:
    mean, low, high = (round(value * _PERCENT) for value in rate)
    return f"{mean:>3}% [{low:>3},{high:>3}]"


def print_summary(records: list[dict[str, Any]]) -> None:
    """Print one line per (model, arm), then the same broken down by task family."""
    rows = summarize(records)
    if not rows:
        print("no completed episodes")
        return
    print(
        f"\n{'model':<28} {'arm':<20} {'n':>4}  {'task pass':<14} {'well-formed':<14} {'tokens':>6} {'tok/s':>5} {'first':>5}  failures"
    )
    for row in rows:
        first = "-" if row["first_artifact"] is None else f"{row['first_artifact'] * _PERCENT:.0f}%"
        print(
            f"{row['model'][:28]:<28} {row['arm']:<20} {row['n']:>4}  {_percent(row['pass']):<14} "
            f"{_percent(row['well_formed']):<14} {row['tokens']:>6.0f} {row['tokens_per_s']:>5.0f} {first:>5}  {row['codes'] or ''}"
        )

    families = list(dict.fromkeys(str(record["family"]) for record in records))
    print(f"\ntask pass rate by family\n{'model':<28} {'arm':<20} " + " ".join(f"{family:>9}" for family in families))
    for row in rows:
        cells: list[str] = []
        for family in families:
            scores = [
                float(r["score"])
                for r in records
                if r.get("error") is None and (r["model"], r["arm"], r["family"]) == (row["model"], row["arm"], family)
            ]
            cells.append(f"{sum(scores) / len(scores) * _PERCENT:>8.0f}%" if scores else f"{'-':>9}")
        print(f"{row['model'][:28]:<28} {row['arm']:<20} " + " ".join(cells))
    print(
        "\npass and well-formed: mean with a 95% bootstrap interval. tokens: median pieces per answer. "
        "first: median share of the answer generated before the application sees the first artifact."
    )
