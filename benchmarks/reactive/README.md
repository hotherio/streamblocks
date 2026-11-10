# Reactive benchmarks

Agents that react to events in tokens, not turns. The question: **does a text model that was never
trained for it use an event appended to its own output while it is generating?**

## Steering pilot

The model writes a six-step guide as StreamBlocks blocks (`!!s3:step … !!end`). When step 2 closes,
a correction (`!!e1:event … !!end`) becomes available and is delivered one of three ways:

| Delivery | What happens |
|---|---|
| `turn_boundary` | the model finishes, then the event arrives as a new user turn |
| `cancel_resend` | generation is stopped, the event arrives as a new user turn |
| `inject` | the event is appended to the model's own turn and generation continues, cache kept |

A later block with the same id replaces the earlier one. An episode is **compliant** when all six
steps exist and steps 3–6 follow the correction (regex check, no judge model).

```bash
uv run --with llama-cpp-python python -m benchmarks.reactive.pilot --model path/to/model.gguf
uv run --with pie-client python -m benchmarks.reactive.pilot --backend pie --model qwen3.5-4b
uv run python -m benchmarks.reactive.pilot --summarize runs/reactive/steering.jsonl
```

## Backends

| Backend | How `inject` works | Decoding |
|---|---|---|
| `llamacpp` | tokens appended in a hand-driven decode loop, cache kept | sampled, seeded |
| `pie` | [Pie](https://pie-project.org) runs `pie_inferlet.py` next to the model; the client asks for one token at a time and can append text to the same working set | greedy |

StreamBlocks parses on the client in both cases. Pie inferlets run standard-library Python only, so
the inferlet has no dependencies. The Pie backend needs `pie serve` running; on macOS 15 that means the
WebGPU build (`PIE_FLAVOR=wgpu`) with `max_forward_tokens = 1024` and `max_forward_requests = 8`.

Metrics are token counts, so they do not depend on machine speed:
`reaction_latency_tokens` (event available → delivered), `wasted_tokens` (steps written after the
event and later rewritten), `completion_tokens`, `uncached_prompt_tokens`, `llm_calls`.
`virtual_time_s` turns those counts into seconds under a named cost model (`--cost local|hosted`,
see `clock.py`), so a run replays to the same numbers.

## Gate

Decided before the valid runs: injection is worth pursuing if, on at least one model with 15 episodes
per delivery, `inject` is compliant no more than three episodes less often than `cancel_resend`.

## Results

Pilot of 2026-11-10, llama.cpp, temperature 0.7, 15 episodes per cell (5 scenarios × 3 seeds).
Compliant episodes, then median completion tokens and model calls per episode:

| Model | `turn_boundary` | `cancel_resend` | `inject` |
|---|---|---|---|
| Gemma 4 E4B (Q4_0) | 14/15 · 392 tok · 2 calls | 8/15 · 173 tok · 2 calls | 12/15 · 190 tok · 1 call |
| Llama 3.1 8B (Q4_K_M) | 11/15 · 518 tok · 2 calls | 14/15 · 304 tok · 2 calls | 12/15 · 253 tok · 1 call |

- **Gate passed on both models.** Neither was trained for it, and both follow an injected event about
  as often as one delivered in a user turn.
- `turn_boundary` wastes a median of 138–156 tokens on steps it then rewrites; the other two waste none.
- `inject` resends no prompt: a median of 231–241 prompt tokens per episode against 571–605 for
  `cancel_resend` and 699–806 for `turn_boundary`.
- `cancel_resend` needs a note telling the model it was interrupted. Without it, Gemma treated the event
  as a new request, fixed the first two steps and stopped (3/15 compliant).
- Both models needed one worked example in the system prompt to close blocks reliably. With it, the only
  malformed blocks were 8 in Llama's `turn_boundary` episodes.

Differences of two or three episodes between cells are within noise at this sample size.

Same scenario on Pie 0.6.0 (WebGPU), Qwen3.5-4B, greedy, 5 episodes per cell, `local` cost model:

| `turn_boundary` | `cancel_resend` | `inject` |
|---|---|---|
| 3/5 · 349 tok · 12.1 s | 3/5 · 169 tok · 6.0 s | 5/5 · 256 tok · 8.7 s |

Injection works on Pie as well, with no malformed blocks. Each `begin` on Pie starts a new working set,
so the two-call deliveries re-evaluate the whole prompt (about 560–670 tokens against 230 for `inject`).

## Live dispatch

Steering asks whether the model obeys. Dispatch asks what a late delivery costs. The model assigns ten
jobs to workers, one `!!a3:assign` block per job (`J3 -> ben`), and an assignment takes effect when its
block closes. Meanwhile the world changes at fixed times on the virtual clock: a worker goes offline, a
job is cancelled. The three deliveries are the same as above; a model that has already ended its turn
is woken with a new turn in all three.

- **Stale action**: an assignment that closes after an event it contradicts. It cannot be taken back,
  only corrected by assigning the job again.
- **Compliant**: every event was delivered and every job that is not cancelled ends on an online worker.

```bash
uv run --with llama-cpp-python python -m benchmarks.reactive.pilot --scenario dispatch --model path/to/model.gguf
```

Hypotheses, written before the first run (15 episodes per cell, `local` cost model):

1. `inject` and `cancel_resend` leave at most the assignment already being written when the event
   happens: a median of one stale action or fewer. `turn_boundary` leaves more.
2. `inject` is compliant no more than three episodes less often than `cancel_resend` (the steering gate).
3. `inject` needs fewer model calls and fewer uncached prompt tokens than the other two.

Against injection: more stale actions than `turn_boundary`, or failing hypothesis 2 on both models.

Run of 2026-11-10, llama.cpp, temperature 0.7, 15 episodes per cell (5 scenarios × 3 seeds), 150 jobs
per cell. Compliant episodes, then totals over the cell: stale actions and model calls.

| Model | `turn_boundary` | `cancel_resend` | `inject` |
|---|---|---|---|
| Gemma 4 E4B (Q4_0) | 3/15 · 36 stale · 30 calls | 3/15 · 11 stale · 36 calls | 3/15 · 15 stale · 15 calls |
| Llama 3.1 8B (Q4_K_M) | 8/15 · 38 stale · 30 calls | 3/15 · 7 stale · 36 calls | 3/15 · 16 stale · 15 calls |

- **Hypothesis 1 holds.** Reacting inside the stream cuts stale actions by more than half against
  waiting for the end of the turn (median per episode: 1 against 2).
- **Hypothesis 2 holds only at the floor, so it says nothing.** In every delivery the only scenario that
  reliably passes is the cancelled job, which needs no repair.
- **Hypothesis 3 holds.** `inject` uses one call per episode and evaluates about 270–280 prompt tokens,
  against 720–840 for the other two.
- **Not predicted: models told mid-stream stop using an offline worker but do not go back.** Jobs already
  given to that worker stay there. Told at the end of the turn, Llama rewrites the plan and passes 5 of 12
  offline episodes; interrupted or injected, neither model passes any. Reacting early prevents new
  mistakes and does not repair old ones.
- `cancel_resend` has fewer stale actions than `inject` on Llama (7 against 16), mostly in the scenarios
  with two events.

So the next question for this scenario is repair, not delivery: whether an event that names the jobs
to move, or a state block listing current assignments, gets them moved.

### Repair

`--repair` changes what an event says about work already done. `plain` (above) says only what changed.
`named` adds the jobs to move ("Assign these jobs again, they were given to cy: J3, J6."). `state` adds
the full list of current assignments and leaves the model to find them.

Hypotheses, written before the run. "Offline episodes" are the 12 per cell with a worker going offline.

1. With `named`, `inject` and `cancel_resend` pass at least 6 of 12 offline episodes on at least one
   model (0 of 12 with `plain`).
2. `state` passes fewer offline episodes than `named`, and more than `plain`.
3. Neither variant raises stale actions for `inject` above its `plain` total.

Against injection: `named` still at 0 of 12 for `inject` on both models. Then a model told exactly what
to redo still cannot go back inside its own turn, and repair needs a new turn.

Run of 2026-11-10, same settings. Offline episodes passed out of 12, then stale actions over the 15
episodes of the cell:

| Model | Event | `turn_boundary` | `cancel_resend` | `inject` |
|---|---|---|---|---|
| Gemma 4 E4B | `plain` | 0 · 36 stale | 0 · 11 stale | 0 · 15 stale |
| | `named` | 11 · 35 stale | 4 · 17 stale | 3 · 21 stale |
| | `state` | 6 · 36 stale | 2 · 15 stale | 1 · 12 stale |
| Llama 3.1 8B | `plain` | 5 · 38 stale | 0 · 7 stale | 0 · 16 stale |
| | `named` | 11 · 37 stale | 7 · 9 stale | 8 · 11 stale |
| | `state` | 5 · 40 stale | 0 · 10 stale | 0 · 15 stale |

- **Hypothesis 1 holds on Llama only** (8 of 12 for `inject`, 7 for `cancel_resend`). Gemma reaches 3 and 4.
- **Hypothesis 2 mostly fails.** `state` is below `named` as predicted, but it barely beats `plain` on
  Gemma and does not on Llama: a list of assignments is not enough, the event has to say what to redo.
- **Hypothesis 3 fails for `named` on Gemma** (21 stale against 15) and holds elsewhere.
- Injection is not ruled out: a model told what to redo can go back inside its own turn.
- With `named`, end-of-turn delivery passes 11 of 12 on both models, more than either mid-stream
  delivery. It still executes three times as many stale actions as `inject` on Llama.
- Gemma's mid-stream failures are momentum: right after the event it writes the next assignment of its
  round-robin to the offline worker (`J6 -> cy`), then carries on correctly without repairing.

Reacting early and repairing well pull in opposite directions here: the earlier the model is told, the
fewer mistakes it makes and the less likely it is to go back over them. An event should carry the
repair to do, not only the change.

## Streaming build

The deciding test for injection. The model writes five small Python modules on top of a library whose
documentation is out of date (three scenarios: a method was renamed, a function was removed, values must
now be strings). Files are artifact blocks (`XmlTagSyntax`, the built-in `file` block). Each file is
checked when its block closes, by running its tests in a subprocess; the result is known one virtual
second later. Only failures are reported, as an event carrying the error. The first error says what changed.

- **Failed checks**: files written on a wrong assumption. **Compliant**: the latest version of all five passes.
- Hosted models run through an OpenAI-compatible API (`--backend hosted`), which can only do
  `turn_boundary` and `cancel_resend`. For them the run also records wall-clock time, and per call the
  time to first token and the prompt tokens served from the provider's cache.

```bash
uv run --with llama-cpp-python python -m benchmarks.reactive.pilot --scenario build --model path/to/model.gguf
uv run --with openai python -m benchmarks.reactive.pilot --scenario build --backend hosted --model gpt-4.1-mini
```

Hypotheses and decision rule, written before the first run (9 episodes per cell):

1. Reacting mid-stream (`cancel_resend`, `inject`) leaves a median of at most 2 failed checks;
   `turn_boundary` leaves 5.
2. Reacting mid-stream finishes sooner than `turn_boundary`: in wall-clock time on hosted models, in
   virtual time on local ones.
3. **Decision on injection.** On hosted models, the most injection could save over `cancel_resend` is the
   time to first token of the calls made to deliver an event. If that is under 10% of the episode's
   wall-clock time, and `inject` is not compliant more often than `cancel_resend` on the local models,
   injection is dropped as the headline and kept as a cost optimisation for self-hosted runtimes. At 25%
   or more it is material. In between, undecided.
4. Resent prompts are mostly served from the provider's cache (reported, no threshold).

## Limits

- Five scenarios, 15 episodes per cell: enough for a go/no-go, not for effect sizes.
- The regex check accepts a guide that mentions the new term once and avoids the old one.
- Dispatch seeds differ little: the task leaves the model few choices, so 15 episodes are closer to 5.
- Hosted models are not covered yet (they can only do `turn_boundary` and `cancel_resend`).
- The Pie backend asks for one token per round trip, which keeps runs deterministic but does not use
  Pie's batching; throughput there is not measured.
- On llama.cpp the cache is kept in all three deliveries, so `uncached_prompt_tokens` understates
  what `cancel_resend` costs on an API without prefix caching (`resent_prompt_tokens` is that cost).
