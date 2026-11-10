"""Pie backend: a thin inferlet generates next to the model; StreamBlocks stays on the client.

Needs a running `pie serve` and the `pie-client` package.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pie_client import Event, PieClient

if TYPE_CHECKING:
    from benchmarks.reactive.backend import Message

_INFERLET = Path(__file__).with_name("pie_inferlet.py")


class PieBackend:
    def __init__(self, url: str = "ws://127.0.0.1:8080") -> None:
        self._loop = asyncio.new_event_loop()
        self._client = PieClient(url)
        self._process = self._loop.run_until_complete(self._launch())
        self.prompt_tokens = 0
        self.uncached_prompt_tokens = 0

    def set_seed(self, seed: int) -> None:
        """Decoding is greedy, so the seed has no effect."""

    def begin(self, messages: list[Message]) -> None:
        tokens = int(self._request({"op": "begin", "messages": messages})["prompt_tokens"])
        self.prompt_tokens += tokens
        self.uncached_prompt_tokens += tokens

    def next_piece(self) -> str | None:
        return self._request({"op": "next"})["piece"]

    def inject(self, text: str) -> int:
        return int(self._request({"op": "inject", "text": text})["injected_tokens"])

    def close(self) -> None:
        self._loop.run_until_complete(self._close())
        self._loop.close()

    async def _launch(self) -> Any:
        await self._client.__aenter__()
        await self._client.authenticate("reactive-benchmark")
        return await self._client.launch_process(await self._client.install_program(str(_INFERLET)))

    async def _close(self) -> None:
        await self._process.signal(json.dumps({"op": "close"}))
        await self._process.result()
        await self._client.__aexit__(None, None, None)

    def _request(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._loop.run_until_complete(self._exchange(payload))

    async def _exchange(self, payload: dict[str, Any]) -> dict[str, Any]:
        await self._process.signal(json.dumps(payload))
        while True:
            event, reply = await self._process.recv()
            if event == Event.Message:
                return json.loads(reply)
            if event in (Event.Return, Event.Error):
                msg = f"Pie inferlet stopped: {event} {reply}"
                raise RuntimeError(msg)
