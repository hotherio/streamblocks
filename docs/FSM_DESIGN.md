# Function Signature Models (FSM) Library Design

## Overview

This document captures the design for a Python library implementing Function Signature Models (FSM) - a client-side approach to function calling that uses structured output instead of native LLM function calling mechanisms.

## Problem Statement

Native function calling in LLMs has significant limitations:

| Limitation | Description |
|------------|-------------|
| Limited execution modes | Only "any" (0-1 call) or "required" (≥1 call) |
| No dependency management | Can't use function A's output as function B's input |
| Parallel-only execution | Functions run in parallel, no sequencing |
| Provider inconsistency | Different implementations across providers |
| Simple parameters only | No Pydantic objects as inputs |

**Example problem**: LLM wants to call `generate_image()` → `upload_image()` → `share_link()`, but native function calling can't express that `upload_image` depends on `generate_image`'s output.

## FSM Solution

Client-side function calling using structured output:

```
Python Function → inspect signature → Pydantic Model → Structured Output Schema
```

**Key innovations:**
- **Dependency DAG**: Functions have `function_id`, `parents_ids`, `children_ids`
- **Output References**: `FunctionOutputRef` lets parameters reference other functions' outputs
- **Single-call workflows**: Multi-step tasks in one LLM call with proper dependency resolution
- **Provider agnostic**: Works with any LLM supporting structured output

## Design Principles

1. **Pydantic as universal interchange** - Core output is a Pydantic model for instant compatibility
2. **Framework-agnostic core** - No mandatory dependencies on LiteLLM, PydanticAI, etc.
3. **Execution separate from planning** - User controls when/how functions run
4. **Type-safe throughout** - Generics preserve function signatures
5. **Lightweight** - Not another agent framework, focused on function calling

## Framework Compatibility

### LiteLLM Integration
```python
from litellm import completion
from fsm import FunctionSet

fs = FunctionSet([search_web, summarize])

response = completion(
    model="gpt-4o",
    messages=[...],
    response_format=fs.to_pydantic_model()  # Direct Pydantic support
)

results = fs.resolve_and_execute(response.choices[0].message.content)
```

### OpenRouter Integration
```python
response = client.chat.completions.create(
    model="openai/gpt-4o",
    messages=[...],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "function_calls",
            "schema": fs.to_json_schema(),
            "strict": True
        }
    },
    extra_body={"provider": {"require_parameters": True}}
)
```

### PydanticAI Integration
```python
from pydantic_ai import Agent
from fsm import FunctionSet

fs = FunctionSet([search_web, summarize])

agent = Agent(
    'openai:gpt-4o',
    output_type=fs.to_pydantic_model(),
    system_prompt="Plan function calls to complete the user's request."
)

result = await agent.run("Find and summarize news about AI")
executed = fs.resolve_and_execute(result.output)
```

## StreamBlocks Integration

### Synergy Overview

| StreamBlocks | FSM | Together |
|--------------|-----|----------|
| Detects structured blocks in streams | Defines function call schemas | Real-time function call detection |
| Emits events as blocks are parsed | Resolves dependencies between calls | Progressive execution as blocks arrive |
| Handles any block syntax | Validates against function signatures | Type-safe function extraction |
| Provider-agnostic streaming | Provider-agnostic function calling | End-to-end streaming function execution |

### Use Case: Streaming Function Calls

LLMs emit function calls as blocks within a larger response:

```markdown
Let me help you with that research task.

!!func:search_web
query: "latest AI safety papers 2024"
!!end

I'll analyze what I find and then summarize:

!!func:analyze_papers
papers: $ref(search_web)
!!end
```

**Benefits:**
- Execute functions as soon as detected (don't wait for full response)
- Show function execution status alongside streaming text
- Independent functions run concurrently
- Lower latency, progressive UI

### Architecture: FSM as StreamBlocks Syntax

```python
from streamblocks import BaseSyntax, DetectionResult, ParseResult
from fsm import FunctionSet, FunctionCall

class FunctionCallSyntax(BaseSyntax):
    """StreamBlocks syntax for FSM function calls."""

    def __init__(self, function_set: FunctionSet):
        self.function_set = function_set

    def detect_line(self, line: str, candidate) -> DetectionResult:
        if line.startswith("!!func:"):
            func_name = line[7:].strip()
            return DetectionResult(
                is_opening=True,
                metadata={"function_name": func_name}
            )
        if line == "!!end":
            return DetectionResult(is_closing=True)
        return DetectionResult()

    def parse_block(self, candidate, block_class) -> ParseResult:
        func_name = candidate.inline_metadata["function_name"]
        params = yaml.safe_load("\n".join(candidate.content_lines))
        func_model = self.function_set.get_function_model(func_name)
        validated = func_model(**params)
        return ParseResult(success=True, content=FunctionCallContent(call=validated))
```

### Integration Pattern

```python
from streamblocks import StreamBlockProcessor, Registry
from fsm import FunctionSet
from fsm.streamblocks import FunctionCallSyntax, FunctionExecutor

fs = FunctionSet([search_web, summarize])
syntax = FunctionCallSyntax(fs)
registry = Registry(syntax=syntax)
processor = StreamBlockProcessor(registry)
executor = FunctionExecutor(fs)

async for event in processor.process_stream(llm_stream):
    match event:
        case TextDeltaEvent(delta=text):
            print(text, end="", flush=True)

        case BlockOpenedEvent(syntax="function_call"):
            print(f"\n⏳ Preparing {event.inline_metadata['function_name']}...")

        case BlockExtractedEvent(block=block):
            call = block.content.call
            executor.queue(call)
            if executor.can_execute(call):
                result = await executor.execute(call)
                print(f"✅ {call.name}: {result}")

await executor.resolve_remaining()
```

## Package Structure

```
fsm/
├── __init__.py              # Public API
├── core/
│   ├── function.py          # @function decorator, BaseFunction
│   ├── set.py               # FunctionSet class
│   ├── schema.py            # Schema generation (Pydantic + JSON Schema)
│   ├── resolver.py          # Dependency resolution
│   ├── executor.py          # Function execution
│   └── types.py             # FunctionOutputRef, FunctionCall, etc.
├── streamblocks/            # StreamBlocks integration (optional)
│   ├── syntax.py            # FunctionCallSyntax
│   ├── executor.py          # Real-time streaming executor
│   └── events.py            # FunctionQueuedEvent, FunctionExecutedEvent
├── adapters/                # Optional convenience wrappers
│   ├── litellm.py           # fsm_completion() helper
│   ├── openrouter.py        # OpenRouter-specific helpers
│   └── pydantic_ai.py       # FSMAgent wrapper
└── py.typed                 # PEP 561 marker
```

## Core API Design

```python
from fsm import function, FunctionSet

@function
def search_web(query: str) -> str:
    """Search the web for information."""
    ...

@function
def summarize(text: str) -> str:
    """Summarize the given text."""
    ...

# Create function set
fs = FunctionSet([search_web, summarize])

# Get Pydantic model class (for LiteLLM, PydanticAI)
FunctionCallPlan = fs.to_pydantic_model()

# Get raw JSON schema (for OpenRouter, raw APIs)
schema = fs.to_json_schema()

# After LLM response - resolve dependencies and execute
results = fs.resolve_and_execute(llm_response)
```

## Comparison with Existing Approaches

### vs PydanticAI / Agno
- **They are model clients** that own the conversation lifecycle
- **FSM is function middleware** that works with any existing client
- FSM is more lightweight and composable

### vs Native Function Calling
- Native: limited modes, no dependencies, provider-specific
- FSM: DAG execution, dependency resolution, provider-agnostic

## Key Value Propositions

1. **Dependency resolution** - The killer feature missing from native function calling
2. **Single-call workflows** - Multi-step tasks without round-trips
3. **Framework agnostic** - Works with any client via Pydantic/JSON Schema
4. **StreamBlocks synergy** - Real-time progressive execution

## References

- [FSM Concept Article](https://quemy.info/2025-15-06-signature-function-models.html)
- [FSM Tutorial Series](https://quemy.info/2025-15-06-tutorial-fsm-1.html)
- [FSM GitHub Repository](https://github.com/hotherio/FSM)
- [LiteLLM Structured Outputs](https://docs.litellm.ai/docs/completion/json_mode)
- [OpenRouter API](https://openrouter.ai/docs/api/reference/parameters)
- [PydanticAI Output Types](https://ai.pydantic.dev/output/)
