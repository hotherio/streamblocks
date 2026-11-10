"""Thin Pie inferlet: the client drives generation one token at a time and may append text.

Runs inside Pie (standard library only). Requests are JSON messages:
  {"op": "begin", "messages": [...]}   start a new assistant turn
  {"op": "next"}                       generate one token; replies {"piece": str | null}
  {"op": "inject", "text": "..."}      append text to the turn in progress, cache kept
  {"op": "close"}                      end the session
Decoding is greedy.
"""

import json

from inferlet import chat, model, session
from inferlet.eta import ForwardPass, Pipeline, StateGeometry, WorkingSet, intrinsics, reduce_argmax

STOP = set(chat.stop_tokens())
ROLES = {"system": chat.system, "user": chat.user, "assistant": chat.assistant}


async def forward(ws, pipe, tokens):
    fwd = ForwardPass()
    fwd.embed(tokens)
    fwd.state([ws], StateGeometry.folding())
    next_token = fwd.epilogue(lambda: reduce_argmax(intrinsics.output(0, "logits")))
    pipe.submit(fwd)
    return await next_token


async def main(input: dict) -> dict:
    pipe = Pipeline()
    ws, pending, turn, sent = None, [], [], ""
    while True:
        request = json.loads(await session.receive())
        op = request["op"]
        if op == "close":
            break
        if op == "begin":
            ws = WorkingSet()
            pending = [t for m in request["messages"] for t in ROLES[m["role"]](m["content"])]
            pending += chat.cue_without_thinking()
            turn, sent = [], ""
            reply = {"prompt_tokens": len(pending)}
        elif op == "inject":
            extra = list(model.encode(request["text"]))
            pending += extra
            turn += extra
            sent = model.decode(turn)
            reply = {"injected_tokens": len(extra)}
        else:
            token = await forward(ws, pipe, pending)
            if token in STOP:
                reply = {"piece": None}
            else:
                turn.append(token)
                pending = [token]
                text = model.decode(turn)
                reply = {"piece": text[len(sent) :]}
                sent = text
        session.send(json.dumps(reply))
    pipe.close()
    return {}
