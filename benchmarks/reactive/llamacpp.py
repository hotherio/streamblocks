"""llama.cpp backend with true mid-stream injection (the model's cache is kept)."""

from __future__ import annotations

import codecs
from typing import TYPE_CHECKING, Any

import llama_cpp
import numpy as np
from llama_cpp.llama_chat_format import Jinja2ChatFormatter

if TYPE_CHECKING:
    from benchmarks.reactive.backend import Message

_CHAT_TEMPLATE_KEY = "tokenizer.chat_template"
_MAX_SEED = 2**31


class LlamaCppBackend:
    """Hand-driven decode loop: evaluate, sample one token, repeat."""

    def __init__(self, model_path: str, *, n_ctx: int = 8192, temperature: float = 0.7, seed: int = 0) -> None:
        self._llm = llama_cpp.Llama(model_path, n_ctx=n_ctx, n_gpu_layers=-1, seed=seed, verbose=False)
        self._vocab = llama_cpp.llama_model_get_vocab(self._llm.model)
        self._formatter = Jinja2ChatFormatter(
            template=self._llm.metadata[_CHAT_TEMPLATE_KEY],
            bos_token=self._special(self._llm.token_bos()),
            eos_token=self._special(self._llm.token_eos()),
        )
        self._temperature = temperature
        self._rng = np.random.default_rng(seed)
        self._decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        self.prompt_tokens = 0
        self.uncached_prompt_tokens = 0

    def set_seed(self, seed: int) -> None:
        self._rng = np.random.default_rng(seed)

    def begin(self, messages: list[Message]) -> None:
        messages_any: Any = messages
        prompt = self._formatter(messages=messages_any).prompt
        tokens = self._llm.tokenize(prompt.encode(), add_bos=False, special=True)
        cached = self._llm.input_ids[: self._llm.n_tokens].tolist()
        keep = 0
        # Always re-evaluate at least the last token so there are logits to sample from.
        while keep < min(len(cached), len(tokens) - 1) and cached[keep] == tokens[keep]:
            keep += 1
        self._llm.n_tokens = keep
        self._llm.eval(tokens[keep:])
        self._decoder.reset()
        self.prompt_tokens += len(tokens)
        self.uncached_prompt_tokens += len(tokens) - keep

    def next_piece(self) -> str | None:
        # `sample` builds a new sampler from the model seed on every call, so the seed must change per token.
        self._llm.set_seed(int(self._rng.integers(_MAX_SEED)))
        token = self._llm.sample(temp=self._temperature)
        if llama_cpp.llama_vocab_is_eog(self._vocab, token):
            return None
        self._llm.eval([token])
        return self._decoder.decode(self._llm.detokenize([token]))

    def inject(self, text: str) -> int:
        tokens = self._llm.tokenize(text.encode(), add_bos=False, special=False)
        self._llm.eval(tokens)
        return len(tokens)

    def _special(self, token: int) -> str:
        return self._llm.detokenize([token], special=True).decode()
