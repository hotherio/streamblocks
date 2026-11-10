# Artifact stream demo

A model writes files inside its answer; the browser shows them filling in, validated and applied as
each block closes.

```bash
# Replay a canned answer (no model needed)
uv run python -m demos.artifact_stream.server

# A local GGUF model, in-process
uv run --with llama-cpp-python python -m demos.artifact_stream.server --gguf path/to/model.gguf

# Any OpenAI-compatible server
uv run --with openai python -m demos.artifact_stream.server --base-url http://localhost:1234/v1 --model my-model
```

Open http://127.0.0.1:8791.

## What to look at

| Control | What it shows |
|---|---|
| **Example: small package** | Four files and one patch stream into the Files pane; each tab turns solid when its block closes and the patch is applied to the file written earlier. |
| **Example: tries to write ../.env** with **Guard** on | The second file is rejected on its opening line, before any of its content is generated, and the generation stops. Compare "pieces generated" with the guard off. |
| **Grammar** | The model is constrained by `Registry.to_grammar()`, so it cannot produce a malformed block. Has an effect with a GGUF model; servers differ in how they accept grammars, and the replay ignores it. |

## How it works

`server.py` is about 250 lines of standard library plus StreamBlocks:

1. `Registry(syntax=XmlTagSyntax(), blocks=ARTIFACT_BLOCKS)` defines the format; the same registry
   produces the system prompt and the grammar.
2. Each piece from the model goes through `StreamBlockProcessor.process_chunk`.
3. Parser events become server-sent events: text lines, block start, content lines, block end
   (the file is written or patched), block error.
4. With the guard on, `path_within("src", "tests", "docs")` runs on every block from its opening
   line and `abort_stream_on_failure` stops the loop that pulls pieces from the model.
