# Artifact benchmarks

Models often write files and edits inside their answer rather than as tool calls. These benchmarks
ask: **do StreamBlocks blocks carry those artifacts more reliably than the usual alternatives, and
does a generated grammar help on local models?**

Everything is scored deterministically (tests run in a subprocess, exact comparisons). There is no
judge model.

## Arms

| Arm | How the model is asked for files | How they are read back |
|---|---|---|
| `xml` | `XmlTagSyntax` with the built-in file and patch blocks; prompt from `Registry.to_prompt()` | StreamBlocks, while streaming |
| `xml+grammar` | same, constrained by `Registry.to_grammar()` | same |
| `xml-noex`, `xml-noex+grammar` | same two, but the prompt has no worked example | same |
| `frontmatter`, `frontmatter+grammar` | `DelimiterFrontmatterSyntax`, same blocks | same |
| `fenced` | fenced code blocks whose info string is the path | regular expression, at the end |
| `json` | one JSON object `{"files": [{"path", "content"}]}` | `json.loads`, at the end |
| `json+schema` | same, constrained by a JSON schema | same |

`json` stands in for files carried in tool-call arguments: the content is a JSON string, so every
quote, backslash and line break must be escaped. It is not a provider's native tool-calling API.

## Tasks

| Family | Tasks | Check |
|---|---|---|
| function | `slugify`, `duration`, `rle` | hidden assertions run against the file |
| project | `shapes`, `inventory` (three files each) | hidden assertions import the package |
| edit | `edit_case`, `edit_add` (change an existing 40-line file) | hidden assertions; the unchanged file fails |
| verbatim | `verbatim_regex`, `verbatim_json`, `verbatim_shell` | the saved file equals the given text exactly |
| document | `guide` (markdown that itself contains code fences) | required headings, fences and lines present |

The verbatim tasks isolate transport: the model only has to copy text full of quotes and
backslashes, so a failure is the format's, not the model's reasoning.

## Hypotheses (written before the first run)

1. **Grammar removes malformed output.** With a grammar, the well-formed rate of block arms is 100%
   up to truncation. Without one it is lower on small models, most of all without a worked example.
2. **A worked example does most of the work.** `xml` is close to `xml+grammar`; `xml-noex` is clearly
   worse than both. (Reported by the reactive pilot on two models; to be confirmed here.)
3. **Blocks beat JSON on escape-heavy content.** On the verbatim family, block arms pass more often
   than `json` and `json+schema`, because nothing has to be escaped.
4. **Fences break on documents that contain fences.** `fenced` fails `guide` more often than the
   block arms.
5. **Patches save tokens on edits.** On the edit family, block arms use fewer completion tokens than
   arms that rewrite the whole file, at a comparable pass rate.
6. **Grammar has a speed cost.** Tokens per second are lower with a grammar.

## What would count against StreamBlocks

- Grammar arms that are not near 100% well-formed (other than truncation): the grammar is wrong.
- Block arms no better than `json+schema` on the verbatim family: the escaping argument does not hold
  for that model.
- A lower task pass rate with a grammar than without: constraining the format hurts the content.

Results are reported as they come out, including these.

## Running

```bash
# A GGUF model in-process (grammars are applied natively by llama.cpp)
uv run --with llama-cpp-python python -m benchmarks.artifacts.run --gguf path/to/model.gguf --seeds 3

# An OpenAI-compatible server; the grammar request field depends on the server
uv run --with openai python -m benchmarks.artifacts.run --base-url http://localhost:1234/v1 --model my-model

# Summarise a run (no model needed)
uv run python -m benchmarks.artifacts.run --summarize runs/artifacts/pilot.jsonl

# Parser only: chunking invariance and throughput
uv run python -m benchmarks.artifacts.parser_bench
```

Episodes are appended to a JSONL file as they finish and a re-run skips the ones already there.
The record (`episode.py`) shares its optional fields with `benchmarks/reactive`.

Task checks execute the code a model wrote, in a subprocess with a timeout. The tasks are small and
benign, but run sweeps only with models and prompts you trust.

## Results

Pilot of 10 November 2026: two local models, 11 tasks, 3 seeds, so **33 episodes per arm and per
model** (6 to 9 per task family). Run in-process with llama-cpp-python 0.3.36 on Apple silicon,
temperature and token limit (1200) left at the harness defaults. Intervals are 95% bootstrap
intervals. At this sample size a difference under about 20 points between two arms is not
established.

### How the numbers were produced (read this first)

The block arms were run twice. The first round is not a fair measurement and is reported only so
the change is visible.

- **Round 1** used a prompt that said blocks *can* be used, while the `fenced` and `json` arms were
  told what they *must* write. Llama 3.1 8B answered in Markdown in most block episodes. Round 1
  also ran with two grammar defects, since fixed in the library: an answer with no block was
  accepted, and a line break was required after the closing marker, which pushed a model that stops
  right there to keep writing until the token limit.
- **Round 2** gives block arms an instruction as firm as the baselines', requires at least one block
  in grammar arms (`min_blocks=1`), and uses the fixed grammar. The `fenced`, `json` and
  `json+schema` records are the round 1 ones: their prompts did not change.

The prompt was changed after seeing round 1 data. Round 2 is therefore a pilot result to be
confirmed on models and seeds not used to tune the prompt.

### Round 2

Task pass rate, then well-formed rate.

| Arm | Gemma 4 E4B (Q4_0) | Llama 3.1 8B Instruct (Q4_K_M) |
|---|---|---|
| `xml` | 76% [61, 88] / 91% | 36% [21, 52] / 76% |
| `xml+grammar` | 76% [61, 88] / 91% | 39% [24, 55] / 88% |
| `xml-noex` | 0% / 0% | 0% / 0% |
| `xml-noex+grammar` | 48% [30, 67] / 79% | 0% / 3% |
| `frontmatter` | 82% [67, 94] / 97% | 36% [21, 52] / 79% |
| `frontmatter+grammar` | 82% [67, 94] / 97% | 36% [21, 52] / 85% |
| `fenced` | 24% [9, 39] / 97% | 27% [12, 42] / 97% |
| `json` | 42% [24, 61] / 55% | 30% [15, 45] / 39% |
| `json+schema` | 56% [41, 72] / 94% (n=32) | 36% [21, 55] / 97% |

Task pass rate by family (function 9, project 6, edit 6, verbatim 9, document 3 episodes per cell):

| Model | Arm | function | project | edit | verbatim | document |
|---|---|---|---|---|---|---|
| Gemma | `xml` | 78% | 100% | 83% | 44% | 100% |
| Gemma | `frontmatter` | 89% | 100% | 100% | 44% | 100% |
| Gemma | `fenced` | 0% | 0% | 100% | 22% | 0% |
| Gemma | `json+schema` | 88% | 100% | 33% | 0% | 100% |
| Llama | `xml` | 22% | 100% | 0% | 33% | 33% |
| Llama | `frontmatter` | 44% | 67% | 0% | 11% | 100% |
| Llama | `fenced` | 22% | 33% | 67% | 11% | 0% |
| Llama | `json+schema` | 33% | 100% | 0% | 0% | 100% |

Median completion tokens on the edit family:

| Arm | Gemma | Llama |
|---|---|---|
| `xml` | 164 (5/6 pass) | 209 (0/6) |
| `frontmatter` | 168 (6/6) | 172 (0/6) |
| `fenced` | 366 (6/6) | 323 (4/6) |
| `json+schema` | 442 (2/6) | 368 (0/6) |

### Against the hypotheses

1. **Grammar removes malformed output: not confirmed.** With a worked example, grammar arms are 85%
   to 97% well-formed, not 100%. The rest is truncation at the token limit, and patches that are
   well-formed but do not apply (counted as malformed here). On Gemma the grammar changes nothing
   once an example is given. On Llama it lifts the well-formed rate (76% to 88% for XML) without
   lifting the task pass rate.
2. **A worked example does most of the work: confirmed on both models.** Without one, `xml-noex` is
   at 0% on both. Grammar rescues that arm on Gemma (48%) and not on Llama, which writes `<file ...>`
   tags as free text until the token limit.
3. **Blocks beat JSON on escape-heavy content: suggestive.** Both JSON arms pass 0 of 9 verbatim
   episodes on both models; block arms pass 1 to 4 of 9. Small cells.
4. **Fences break on documents that contain fences: confirmed.** `fenced` passes 0 of 3 on `guide`
   on both models. Block arms pass 3 of 3 on Gemma; on Llama `frontmatter` passes 3 of 3 and `xml`
   1 of 3.
5. **Patches save tokens on edits: true on Gemma, false on Llama.** On Gemma, patches pass at well
   under half the tokens of a full rewrite. On Llama every patch fails: the model fills the hunk
   format correctly but uses it wrongly, for example replacing the existing function instead of
   adding one after it. `fenced`, which rewrites the file, passes 4 of 6.
6. **Grammar has a speed cost: confirmed**, about 8 against 11 to 12 tokens per second on Gemma and
   15 against 18 on Llama. Absolute speeds vary between runs because the machine was shared.

### Against StreamBlocks

- Grammar arms are not at 100% well-formed (criterion 1 above).
- On Llama 3.1 8B, block arms are **no better overall than `json+schema`** (36% to 39% against 36%),
  and worse than `fenced` on edits. The advantage seen on Gemma (76% to 82% against 56%) does not
  carry over to this model.
- The first frontmatter grammar lowered the task pass rate on Gemma from 76% to 28% in round 1,
  because it forced quoted values the model does not naturally write. Fixed since; with the fix the
  grammar arm equals the arm without grammar.
- A grammar cannot stand in for a prompt: without a worked example, no edit task passes on either
  model, with or without grammar.

### Round 1, for the record

Block arms only, same tasks and seeds, permissive prompt and earlier grammar.

| Arm | Gemma: pass / well-formed | Llama: pass / well-formed |
|---|---|---|
| `xml` | 79% / 97% | 0% / 3% |
| `xml+grammar` | 79% / 97% | 6% / 12% |
| `xml-noex` | 12% / 15% | 0% / 0% |
| `xml-noex+grammar` | 45% / 79% | 0% / 6% |
| `frontmatter` | 76% / 94% | 0% / 3% |
| `frontmatter+grammar` | 28% / 62% | 6% / 9% |

### Parser only

400 artifacts are extracted identically under 20 random chunkings of the stream, at about 6.3 MB/s
(measured while a model was running on the same machine).
