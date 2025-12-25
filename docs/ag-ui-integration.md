# Streamblocks and AG-UI Integration Analysis

This document analyzes the relationship between Streamblocks and the [AG-UI (Agent-User Interaction) Protocol](https://docs.ag-ui.com), exploring integration scenarios and strategic recommendations.

## Overview

### What is AG-UI?

AG-UI is an open, lightweight, event-based protocol that standardizes how AI agents connect to user-facing applications. Developed by CopilotKit, it provides:

- **Bidirectional communication** between agents and UIs
- **~16 standard event types** covering messages, tool calls, state, and control
- **Transport-agnostic design** (SSE, WebSockets, webhooks)
- **Human-in-the-loop controls** (interrupts, approvals, retries)
- **State management** with RFC 6902 JSON Patch operations

AG-UI complements MCP (agent-to-tools) and A2A (agent-to-agent) protocols in the AI ecosystem.

### What is Streamblocks?

Streamblocks is a Python library for real-time extraction and processing of structured blocks from text streams. It provides:

- **Custom syntax parsing** (delimiter, frontmatter, markdown formats)
- **Type-safe Pydantic models** with generics (`Block[TMetadata, TContent]`)
- **Streaming validation** with rejection of malformed blocks
- **Provider adapters** for Gemini, OpenAI, Anthropic
- **Event-driven architecture** for real-time processing

## Comparison

### Scope and Purpose

| Aspect | Streamblocks | AG-UI |
|--------|-------------|-------|
| **Type** | Python library | Protocol specification |
| **Focus** | Parse structured blocks from text | Agent-UI communication |
| **Direction** | Unidirectional (parsing output) | Bidirectional |
| **Primary question** | "How do I extract typed data from LLM text?" | "How do agents and UIs communicate?" |

### Event Models

**Streamblocks** has 6 events focused on block extraction:

| Event | Purpose |
|-------|---------|
| `RAW_TEXT` | Text outside blocks |
| `TEXT_DELTA` | Real-time character streaming |
| `BLOCK_OPENED` | Block opening detected |
| `BLOCK_DELTA` | Partial block updates |
| `BLOCK_EXTRACTED` | Complete validated block |
| `BLOCK_REJECTED` | Block validation failed |

**AG-UI** has broader event categories:

| Category | Events |
|----------|--------|
| **Lifecycle** | `RunStarted`, `RunFinished`, `RunError`, `StepStarted`, `StepFinished` |
| **Text Messages** | `TextMessageStart`, `TextMessageContent`, `TextMessageEnd` |
| **Tool Calls** | `ToolCallStart`, `ToolCallArgs`, `ToolCallEnd`, `ToolCallResult` |
| **State** | `StateSnapshot`, `StateDelta`, `MessagesSnapshot` |
| **Activity** | `ActivitySnapshot`, `ActivityDelta` |
| **Special** | `Raw`, `Custom` |

### Feature Comparison

| Concern | Streamblocks | AG-UI |
|---------|-------------|-------|
| Syntax parsing | Custom grammars, boundary detection | Not addressed |
| Partial block handling | Built-in state machine | Not addressed |
| Type validation | Pydantic models, parse decorators | JSON schema |
| Communication protocol | None | Full specification |
| Bidirectional flow | No | Yes |
| Human-in-the-loop | No | Built-in |
| State management | Block-level only | Full RFC 6902 patches |

### Architectural Positioning

These systems operate at different layers:

```
┌─────────────────────────────────────────────────┐
│                  Frontend (UI)                  │
├─────────────────────────────────────────────────┤
│              AG-UI Protocol Layer               │
│   (TextMessage, ToolCall, State, Control)       │
├─────────────────────────────────────────────────┤
│            Streamblocks (optional)              │
│   (Parse embedded blocks from text content)     │
├─────────────────────────────────────────────────┤
│           LLM / Agent Backend                   │
└─────────────────────────────────────────────────┘
```

Streamblocks is **complementary**, not competing with AG-UI.

## Integration Scenarios

### Scenario 1: Streamblocks as AG-UI Content Parser

**Use case**: AG-UI streams raw LLM text; Streamblocks extracts structured blocks and emits them as AG-UI tool calls.

```python
from ag_ui import BaseEvent, ToolCallStart, ToolCallArgs, ToolCallEnd
from streamblocks import StreamBlockProcessor, BlockExtractedEvent

class StreamblocksAGUIBridge:
    """Transforms Streamblocks events into AG-UI events."""

    def __init__(self, processor: StreamBlockProcessor):
        self.processor = processor
        self._tool_call_counter = 0

    async def process_text_message(
        self,
        text_delta: str
    ) -> AsyncIterator[BaseEvent]:
        """Process AG-UI text delta, emit AG-UI tool calls for blocks."""

        for event in self.processor.process_chunk(text_delta):
            if isinstance(event, BlockExtractedEvent):
                block = event.block
                tool_call_id = f"block_{self._tool_call_counter}"
                self._tool_call_counter += 1

                # Emit as AG-UI tool call sequence
                yield ToolCallStart(
                    tool_call_id=tool_call_id,
                    tool_call_name=block.metadata.block_type,
                )
                yield ToolCallArgs(
                    tool_call_id=tool_call_id,
                    delta=block.content.model_dump_json(),
                )
                yield ToolCallEnd(tool_call_id=tool_call_id)
```

**Benefit**: Frontend receives typed tool calls instead of raw text with embedded blocks.

### Scenario 2: AG-UI Adapter for Streamblocks

**Use case**: Streamblocks consumes AG-UI event streams directly via a dedicated adapter.

```python
from streamblocks.adapters.base import StreamAdapter
from ag_ui import BaseEvent

class AGUIAdapter(StreamAdapter[BaseEvent]):
    """Extract text from AG-UI TextMessageContent events."""

    def extract_text(self, event: BaseEvent) -> str | None:
        if event.type == "TEXT_MESSAGE_CONTENT":
            return event.delta
        return None

    def is_complete(self, event: BaseEvent) -> bool:
        return event.type in ("TEXT_MESSAGE_END", "RUN_FINISHED")

    def get_metadata(self, event: BaseEvent) -> dict[str, Any] | None:
        if event.type == "RUN_STARTED":
            return {"thread_id": event.thread_id, "run_id": event.run_id}
        return None
```

**Usage**:

```python
async for event in processor.process_stream(agui_event_stream, adapter=AGUIAdapter()):
    if isinstance(event, BlockExtractedEvent):
        # Handle extracted block
        pass
```

### Scenario 3: Streamblocks Blocks as AG-UI State Deltas

**Use case**: Extracted blocks automatically sync to AG-UI shared state using RFC 6902 JSON Patch.

```python
from ag_ui import StateDelta
from streamblocks import BlockExtractedEvent

def block_to_state_delta(event: BlockExtractedEvent) -> StateDelta:
    """Convert extracted block to AG-UI state patch."""
    block = event.block

    return StateDelta(
        delta=[
            {
                "op": "add",
                "path": f"/blocks/{block.hash_id}",
                "value": {
                    "type": block.metadata.block_type,
                    "id": block.metadata.id,
                    "content": block.content.model_dump(),
                    "line_start": block.line_start,
                    "line_end": block.line_end,
                }
            }
        ]
    )
```

**Benefit**: Frontend state store automatically tracks all extracted blocks.

### Scenario 4: Interactive Block Approval (Human-in-the-Loop)

**Use case**: Use AG-UI's control events to approve/reject blocks before execution.

```
LLM generates block → Streamblocks extracts → AG-UI ActivitySnapshot
                                                      ↓
                                              User approves/rejects
                                                      ↓
                                              Block executed or discarded
```

```python
from ag_ui import ActivitySnapshot, BaseEvent
from streamblocks import StreamBlockProcessor, BlockExtractedEvent

class InteractiveBlockProcessor:
    def __init__(self, processor: StreamBlockProcessor):
        self.processor = processor

    async def process_with_approval(
        self,
        stream
    ) -> AsyncIterator[BaseEvent]:
        async for event in self.processor.process_stream(stream):
            if isinstance(event, BlockExtractedEvent):
                block = event.block

                if self._requires_approval(block):
                    # Emit activity for user review
                    yield ActivitySnapshot(
                        message_id=f"approval_{block.hash_id}",
                        activity_type="block_approval",
                        content={
                            "block_type": block.metadata.block_type,
                            "preview": block.raw_text[:200],
                            "risk_level": self._assess_risk(block),
                        }
                    )

                    # Wait for user decision via AG-UI control event
                    decision = await self._wait_for_approval(block.hash_id)

                    if decision.approved:
                        yield self._block_to_tool_call(block)
                    else:
                        yield self._block_rejected_event(block, decision.reason)

    def _requires_approval(self, block) -> bool:
        # Define approval criteria (e.g., file deletions, sensitive operations)
        return block.metadata.block_type in ("files_operations", "patch")

    def _assess_risk(self, block) -> str:
        # Implement risk assessment logic
        return "medium"
```

### Scenario 5: AG-UI Agent Wrapping Streamblocks

**Use case**: Implement an AG-UI-compliant agent that uses Streamblocks internally.

```python
from uuid import uuid4
from ag_ui import (
    AbstractAgent, RunAgentInput, BaseEvent,
    RunStarted, RunFinished,
    TextMessageStart, TextMessageContent, TextMessageEnd,
    ActivitySnapshot,
)
from streamblocks import (
    StreamBlockProcessor, Registry,
    TextDeltaEvent, BlockExtractedEvent, BlockRejectedEvent,
)

class StreamblocksAgent(AbstractAgent):
    """AG-UI agent that parses blocks from any LLM backend."""

    def __init__(self, registry: Registry, llm_client):
        self.processor = StreamBlockProcessor(registry)
        self.llm = llm_client

    async def run(self, input: RunAgentInput) -> AsyncIterator[BaseEvent]:
        yield RunStarted(thread_id=input.thread_id, run_id=input.run_id)

        message_id = str(uuid4())
        yield TextMessageStart(message_id=message_id, role="assistant")

        # Stream from LLM through Streamblocks
        llm_stream = self.llm.stream(input.messages)

        async for event in self.processor.process_stream(llm_stream):
            match event:
                case TextDeltaEvent():
                    yield TextMessageContent(
                        message_id=message_id,
                        delta=event.delta
                    )

                case BlockExtractedEvent():
                    # Emit block as tool call
                    yield from self._emit_block_as_tool_call(event.block)

                case BlockRejectedEvent():
                    # Emit as activity for debugging
                    yield ActivitySnapshot(
                        message_id=message_id,
                        activity_type="block_error",
                        content={"reason": event.reason}
                    )

        yield TextMessageEnd(message_id=message_id)
        yield RunFinished()

    def _emit_block_as_tool_call(self, block):
        # Implementation for converting block to tool call events
        pass
```

### Scenario 6: Bidirectional State Sync

**Use case**: AG-UI state changes trigger Streamblocks reprocessing for validation.

```python
from ag_ui import StateDelta
from streamblocks import StreamBlockProcessor

class BidirectionalBlockSync:
    """Sync blocks between Streamblocks and AG-UI state."""

    def __init__(self, processor: StreamBlockProcessor):
        self.processor = processor
        self.state = {}  # AG-UI shared state

    async def handle_state_delta(
        self,
        delta: StateDelta
    ) -> AsyncIterator[StateDelta]:
        """Handle incoming AG-UI state changes."""
        for op in delta.delta:
            if op["path"].startswith("/blocks/") and op["op"] == "replace":
                # User edited a block in the UI
                block_id = op["path"].split("/")[2]
                new_content = op["value"]["raw_content"]

                # Re-parse with Streamblocks for validation
                reparse_events = self.processor.process_chunk(new_content)
                for event in self.processor.finalize():
                    if isinstance(event, BlockExtractedEvent):
                        # Emit validated state update
                        yield StateDelta(delta=[{
                            "op": "replace",
                            "path": f"/blocks/{block_id}/validated",
                            "value": event.block.content.model_dump()
                        }])
```

## Scenarios Summary

| Scenario | Direction | Streamblocks Role | AG-UI Role |
|----------|-----------|-------------------|------------|
| **1. Content Parser** | SB → AG-UI | Parse text | Emit tool calls |
| **2. AG-UI Adapter** | AG-UI → SB | Consume events | Provide stream |
| **3. State Deltas** | SB → AG-UI | Extract blocks | Sync state |
| **4. Block Approval** | Bidirectional | Extract & validate | Control flow |
| **5. Agent Wrapper** | SB inside AG-UI | Process LLM output | Protocol compliance |
| **6. Bidirectional Sync** | Both | Re-validate edits | State management |

## Strategic Recommendations

### Value Proposition

Streamblocks has unique value in scenarios where:

1. **Custom syntax parsing** is needed (not just JSON tool calls)
2. **Streaming validation** is required (reject bad blocks immediately)
3. LLMs **don't have native tool calling** or text-based structured output is preferred
4. **Deep Pydantic integration** with generics and parse decorators is valuable

### Positioning

Streamblocks should be positioned as **AG-UI compatible**, not as a subset or competitor:

- AG-UI is a **protocol** (defines what events flow)
- Streamblocks is an **implementation library** (defines how to extract structured content)
- They operate at **different layers** and are complementary

### When to Use Each

| Situation | Recommendation |
|-----------|----------------|
| LLM supports native tool calling | AG-UI tool events directly |
| LLM outputs structured text (markdown, custom formats) | Streamblocks + AG-UI |
| Need custom syntax (patches, file ops, domain-specific) | Streamblocks |
| Want validated Pydantic models from text | Streamblocks |
| Just need chat + standard tools | AG-UI alone |
| Human-in-the-loop without structured extraction | AG-UI alone |

### Implementation Roadmap

#### Phase 1: AG-UI Adapter

Add `AGUIAdapter` to consume AG-UI event streams:

```python
# streamblocks/adapters/agui.py
class AGUIAdapter(StreamAdapter[BaseEvent]):
    """Extract text from AG-UI TextMessageContent events."""
    pass
```

#### Phase 2: AG-UI Emitter

Add `AGUIEmitter` to convert Streamblocks events to AG-UI events:

```python
# streamblocks/integrations/agui/emitter.py
class AGUIEmitter:
    """Convert Streamblocks events to AG-UI protocol events."""

    def emit(self, event: StreamEvent) -> list[BaseEvent]:
        pass
```

#### Phase 3: AG-UI Agent Base Class

Provide a base class for AG-UI-compliant agents using Streamblocks:

```python
# streamblocks/integrations/agui/agent.py
class StreamblocksAGUIAgent(AbstractAgent):
    """Base class for AG-UI agents with Streamblocks parsing."""
    pass
```

#### Phase 4: Documentation and Examples

- Add "Using Streamblocks with AG-UI" guide
- Provide example implementations for common scenarios
- Document event mapping between Streamblocks and AG-UI

## References

- [AG-UI Documentation](https://docs.ag-ui.com)
- [AG-UI GitHub Repository](https://github.com/ag-ui-protocol/ag-ui)
- [AG-UI Events Reference](https://docs.ag-ui.com/concepts/events)
- [AG-UI Agents Documentation](https://docs.ag-ui.com/concepts/agents)
- [CopilotKit AG-UI Overview](https://www.copilotkit.ai/ag-ui)
