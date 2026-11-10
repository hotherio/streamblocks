"""A hosted model behind an OpenAI-compatible API. It cannot inject: an event needs a new call."""

from __future__ import annotations

import importlib
import os
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from benchmarks.reactive.backend import Message


class HostedBackend:
    """Streams one call at a time. Each streamed chunk counts as one token on the virtual clock.

    `call_log` holds what the provider reported for each call: time to first token, and prompt,
    cached and completion tokens. Token counts are missing for calls cancelled before their end.
    """

    can_inject = False

    def __init__(
        self, model: str, *, base_url: str | None = None, api_key_env: str = "OPENAI_API_KEY", temperature: float = 0.7
    ) -> None:
        openai = importlib.import_module("openai")
        self._client = openai.OpenAI(base_url=base_url, api_key=os.environ[api_key_env])
        self._model = model
        self._temperature = temperature
        self._seed = 0
        self._chunks: Any = None
        self._call: dict[str, Any] = {}
        self._started = 0.0
        self.call_log: list[dict[str, Any]] = []
        self.prompt_tokens = 0
        self.uncached_prompt_tokens = 0

    def set_seed(self, seed: int) -> None:
        self._seed = seed

    def begin(self, messages: list[Message]) -> None:
        if self._chunks is not None:
            self._chunks.close()  # cancel the call in progress
        self._call = {"ttft_s": None, "prompt_tokens": None, "cached_tokens": None, "completion_tokens": None}
        self.call_log.append(self._call)
        self._started = time.perf_counter()
        self._chunks = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            stream=True,
            stream_options={"include_usage": True},
            temperature=self._temperature,
            seed=self._seed,
        )

    def next_piece(self) -> str | None:
        for chunk in self._chunks:
            if chunk.usage is not None:
                self._record_usage(chunk.usage)
            piece = chunk.choices[0].delta.content if chunk.choices else None
            if piece:
                if self._call["ttft_s"] is None:
                    self._call["ttft_s"] = round(time.perf_counter() - self._started, 3)
                return piece
        self._chunks = None
        return None

    def inject(self, text: str) -> int:
        raise NotImplementedError(f"a hosted API cannot append {len(text)} characters to a turn in progress")

    def _record_usage(self, usage: Any) -> None:
        details = usage.prompt_tokens_details
        cached = (details.cached_tokens if details else 0) or 0
        self._call.update(
            prompt_tokens=usage.prompt_tokens, cached_tokens=cached, completion_tokens=usage.completion_tokens
        )
        self.prompt_tokens += usage.prompt_tokens
        self.uncached_prompt_tokens += usage.prompt_tokens - cached
