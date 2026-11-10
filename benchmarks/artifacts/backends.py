"""Chat backends: stream one answer, optionally constrained by a grammar or a JSON schema."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from collections.abc import Iterator

Message = dict[str, str]


class ChatBackend(Protocol):
    """Streams the pieces (roughly, tokens) of one answer."""

    name: str
    model: str

    def stream(
        self,
        messages: list[Message],
        *,
        grammar: str | None,
        response_schema: dict[str, Any] | None,
        max_tokens: int,
        temperature: float,
        seed: int,
    ) -> Iterator[str]:
        """Yield the answer piece by piece."""
        ...


class ScriptedBackend:
    """Replays fixed answers, for tests. ``answers`` maps a substring of the user prompt to an answer."""

    name = "scripted"
    model = "scripted"

    def __init__(self, answers: dict[str, str], *, piece_size: int = 7) -> None:
        self._answers = answers
        self._piece_size = piece_size

    def stream(
        self,
        messages: list[Message],
        *,
        grammar: str | None,
        response_schema: dict[str, Any] | None,
        max_tokens: int,
        temperature: float,
        seed: int,
    ) -> Iterator[str]:
        del grammar, response_schema, temperature, seed
        prompt = messages[-1]["content"]
        answer = next((text for key, text in self._answers.items() if key in prompt), "")
        pieces = [answer[i : i + self._piece_size] for i in range(0, len(answer), self._piece_size)]
        yield from pieces[:max_tokens]


class LlamaCppBackend:
    """A GGUF model run in-process with llama-cpp-python (grammars are applied natively)."""

    name = "llamacpp"

    def __init__(self, model_path: str, *, n_ctx: int = 8192) -> None:
        self._llama_cpp = importlib.import_module("llama_cpp")
        self._llm = self._llama_cpp.Llama(model_path, n_ctx=n_ctx, n_gpu_layers=-1, verbose=False)
        self.model = model_path.rsplit("/", 1)[-1]

    def stream(
        self,
        messages: list[Message],
        *,
        grammar: str | None,
        response_schema: dict[str, Any] | None,
        max_tokens: int,
        temperature: float,
        seed: int,
    ) -> Iterator[str]:
        options: dict[str, Any] = {}
        if grammar is not None:
            options["grammar"] = self._llama_cpp.LlamaGrammar.from_string(grammar, verbose=False)
        if response_schema is not None:
            options["response_format"] = {"type": "json_object", "schema": response_schema}
        chunks = self._llm.create_chat_completion(
            messages=messages, stream=True, max_tokens=max_tokens, temperature=temperature, seed=seed, **options
        )
        for chunk in chunks:
            piece = chunk["choices"][0]["delta"].get("content")
            if piece:
                yield piece


class OpenAICompatibleBackend:
    """A server with an OpenAI-compatible chat endpoint (LM Studio, llama-server, Pie, ...).

    ``grammar_field`` is the name of the request field that carries a GBNF
    grammar. It differs between servers; check the server's documentation.
    """

    name = "openai-compatible"

    def __init__(self, base_url: str, model: str, *, grammar_field: str = "grammar", api_key: str = "none") -> None:
        openai = importlib.import_module("openai")
        self._client = openai.OpenAI(base_url=base_url, api_key=api_key)
        self._grammar_field = grammar_field
        self.model = model

    def stream(
        self,
        messages: list[Message],
        *,
        grammar: str | None,
        response_schema: dict[str, Any] | None,
        max_tokens: int,
        temperature: float,
        seed: int,
    ) -> Iterator[str]:
        options: dict[str, Any] = {}
        if grammar is not None:
            options["extra_body"] = {self._grammar_field: grammar}
        if response_schema is not None:
            options["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "files", "schema": response_schema},
            }
        chunks = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
            max_tokens=max_tokens,
            temperature=temperature,
            seed=seed,
            **options,
        )
        for chunk in chunks:
            piece = chunk.choices[0].delta.content if chunk.choices else None
            if piece:
                yield piece
