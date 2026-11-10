"""Virtual time: computed from token counts, so results do not depend on machine or network speed."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CostModel:
    decode_tps: float  # generated tokens per second
    prefill_tps: float  # prompt tokens evaluated per second
    call_overhead_s: float  # fixed latency of starting a model call


COSTS = {
    "local": CostModel(decode_tps=30, prefill_tps=1500, call_overhead_s=0.0),
    "hosted": CostModel(decode_tps=80, prefill_tps=8000, call_overhead_s=0.6),
}


class VirtualClock:
    def __init__(self, cost: CostModel) -> None:
        self.cost = cost
        self.now = 0.0

    def call(self, uncached_prompt_tokens: int) -> None:
        self.now += self.cost.call_overhead_s
        self.prefill(uncached_prompt_tokens)

    def prefill(self, tokens: int) -> None:
        self.now += tokens / self.cost.prefill_tps

    def generated(self, tokens: int = 1) -> None:
        self.now += tokens / self.cost.decode_tps
