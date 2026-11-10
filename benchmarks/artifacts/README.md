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

No results yet. The first pilot (one model, three seeds) is a smoke test of the harness, not a
measurement; numbers will be added here with their sample sizes.
