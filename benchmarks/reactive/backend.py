"""Model backends for reactive benchmarks.

A backend generates one assistant turn piece by piece and accepts text injected into
that turn while it is being generated.
"""

from __future__ import annotations

from typing import Protocol

Message = dict[str, str]


class Backend(Protocol):
    """One model, driven one piece (token) at a time."""

    prompt_tokens: int
    """Prompt tokens submitted across all `begin` calls."""
    uncached_prompt_tokens: int
    """Subset of `prompt_tokens` the model had to evaluate (not served from its cache)."""

    def begin(self, messages: list[Message]) -> None:
        """Start a new assistant turn after `messages`, dropping any turn in progress."""
        ...

    def next_piece(self) -> str | None:
        """Generate the next piece of the turn, or None when the model ends it."""
        ...

    def inject(self, text: str) -> None:
        """Append `text` to the turn in progress; generation continues after it."""
        ...


class ScriptedBackend:
    """Replays fixed pieces, for tests and replay. No model involved.

    `turns[i]` is what the i-th `begin` call generates. After an `inject`, the rest of
    the current turn is replaced by `after_inject`.
    """

    def __init__(self, turns: list[list[str]], after_inject: list[str] | None = None) -> None:
        self._turns = turns
        self._after_inject = after_inject or []
        self._pending: list[str] = []
        self._calls = 0
        self.injected: list[str] = []
        self.prompt_tokens = 0
        self.uncached_prompt_tokens = 0

    def begin(self, messages: list[Message]) -> None:
        self._pending = list(self._turns[self._calls]) if self._calls < len(self._turns) else []
        self._calls += 1
        words = sum(len(message["content"].split()) for message in messages)
        self.prompt_tokens += words
        self.uncached_prompt_tokens += words

    def next_piece(self) -> str | None:
        return self._pending.pop(0) if self._pending else None

    def inject(self, text: str) -> None:
        self.injected.append(text)
        self._pending = list(self._after_inject)
