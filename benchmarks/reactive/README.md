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
uv run python -m benchmarks.reactive.pilot --summarize runs/reactive/pilot.jsonl
```

Metrics are token counts, so they do not depend on machine speed:
`reaction_latency_tokens` (event available → delivered), `wasted_tokens` (steps written after the
event and later rewritten), `completion_tokens`, `uncached_prompt_tokens`, `llm_calls`.

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

## Limits

- Five scenarios, 15 episodes per cell: enough for a go/no-go, not for effect sizes.
- The regex check accepts a guide that mentions the new term once and avoids the old one.
- Hosted models are not covered yet (they can only do `turn_boundary` and `cancel_resend`).
- On llama.cpp the cache is kept in all three deliveries, so `uncached_prompt_tokens` understates
  what `cancel_resend` costs on an API without prefix caching (`resent_prompt_tokens` is that cost).
