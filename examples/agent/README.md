# StreamBlocks Agent Examples

This directory demonstrates how to build AI agents using StreamBlocks with **speculative continuation** - a unique pattern that enables parallel tool execution while the LLM streams continuously.

## Key Innovation: Speculative Continuation

Traditional agent frameworks follow a serial pattern:
```
LLM generates → waits for tool → LLM continues → waits for tool → ...
```

StreamBlocks enables **speculative continuation**:
```
LLM streams continuously → tools execute in parallel → results injected on-the-fly
```

### How It Works

1. **LLM never stops** - The model continues generating text even after emitting a tool call
2. **Tools run in background** - `asyncio.create_task()` launches tools immediately
3. **Smart result injection**:
   - If LLM finished → inject result, start new LLM call
   - If LLM still streaming → cancel stream, inject result, resume
4. **Significant time savings** - Parallel execution vs serial waiting

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Agent                                │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │   @tool     │  │ RunContext   │  │ SpeculativeStream │  │
│  │  decorators │  │   [TDeps]    │  │   (parallel exec) │  │
│  └─────────────┘  └──────────────┘  └───────────────────┘  │
│                           │                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              StreamBlockProcessor                    │   │
│  │   (parses Action and FinalAnswer blocks)            │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Files

| File | Description |
|------|-------------|
| `agent.py` | Main `Agent` class with `@tool` decorator |
| `blocks.py` | `Action` and `FinalAnswer` block definitions |
| `context.py` | `RunContext[TDeps]` for dependency injection |
| `events.py` | Agent events (ActionEvent, ToolStartedEvent, etc.) |
| `executor.py` | Tool executor with retry, timeout support |
| `prompts.py` | System prompt builder |
| `speculative_stream.py` | Core speculative continuation logic |

## Examples

### 01_basic_agent.py

Simple agent with basic tools. Shows decorator-based registration:

```python
agent = Agent(model="gemini-2.5-flash")

@agent.tool_plain
def calculate(expression: str) -> float:
    """Evaluate a math expression."""
    return eval(expression)

result = await agent.run("What is 25 * 4?")
print(result.answer)
```

### 04_speculative_continuation_demo.py (KEY DEMO)

Demonstrates the speculative continuation advantage with:
- Multiple async tools with different execution times
- Real-time timeline visualization
- Comparison with serial execution
- Performance metrics

Run it to see the speedup:
```bash
export GEMINI_API_KEY="your-key"
uv run python examples/agent/04_speculative_continuation_demo.py
```

## API Reference

### Agent

```python
class Agent(Generic[TDeps]):
    def __init__(
        self,
        model: str = "gemini-2.5-flash",
        api_key: str | None = None,
        max_iterations: int = 10,
    ) -> None: ...

    def tool(self, ...) -> Callable:
        """Register a tool that receives RunContext[TDeps]."""

    def tool_plain(self, ...) -> Callable:
        """Register a plain tool (no context)."""

    async def run(self, task: str, deps: TDeps | None = None) -> AgentResult:
        """Run the agent and return final result."""

    async def run_stream(self, task: str, deps: TDeps | None = None) -> AsyncIterator:
        """Run the agent, yielding all events for UI integration."""
```

### RunContext

Pydantic AI-style dependency injection:

```python
@dataclass
class RunContext(Generic[TDeps]):
    deps: TDeps           # Your custom dependencies
    retry: int = 0        # Current retry attempt
    tool_name: str | None # Name of the tool being executed
    tool_id: str | None   # Unique ID for this tool call
```

Example with dependencies:

```python
@dataclass
class AppDeps:
    api_key: str
    db_connection: Connection

agent = Agent[AppDeps](model="gemini-2.5-flash")

@agent.tool
def fetch_user(ctx: RunContext[AppDeps], user_id: int) -> dict:
    # Access ctx.deps.db_connection
    return db.query(user_id)

result = await agent.run("Find user 123", deps=AppDeps(...))
```

### Events

For real-time UI updates:

```python
async for event in agent.run_stream(task):
    if isinstance(event, ActionEvent):
        print(f"Tool call: {event.tool_name}")
    elif isinstance(event, ToolStartedEvent):
        print(f"Tool started in background")
    elif isinstance(event, StreamCancelledEvent):
        print(f"Stream cancelled: {event.reason}")
    elif isinstance(event, ObservationEvent):
        print(f"Result: {event.result}")
    elif isinstance(event, AnswerEvent):
        print(f"Answer: {event.answer}")
```

## Block Format

The agent uses StreamBlocks' delimiter frontmatter syntax:

### Action Block
```
!!start
---
id: action_1
block_type: action
tool_name: calculate
---
expression: "sqrt(16)"
!!end
```

### FinalAnswer Block
```
!!start
---
id: answer_1
block_type: final_answer
tools_called: 2
---
The square root of 16 is 4.
!!end
```

## Comparison with Other Frameworks

| Feature | StreamBlocks Agent | Pydantic AI | LangChain |
|---------|-------------------|-------------|-----------|
| Speculative continuation | ✅ Yes | ❌ No | ❌ No |
| Parallel tool execution | ✅ Native | ⚠️ Manual | ⚠️ Manual |
| Streaming while tools run | ✅ Yes | ❌ Blocks | ❌ Blocks |
| Block-based parsing | ✅ Native | ❌ No | ❌ No |
| Dependency injection | ✅ RunContext | ✅ RunContext | ⚠️ Various |

## Requirements

- Python 3.13+
- `google-genai` package for Gemini
- `GEMINI_API_KEY` or `GOOGLE_API_KEY` environment variable

```bash
uv pip install google-genai
export GEMINI_API_KEY="your-key"
```

## See Also

- [StreamBlocks Documentation](../../README.md)
- [Live Feedback Examples](../live_feedback/README.md) - Similar patterns for user feedback
- [Pydantic AI](https://ai.pydantic.dev/) - Inspiration for the API design
