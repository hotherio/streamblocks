# Streamblocks Architecture Improvement Plan

## Overview

This plan improves Streamblocks across four areas: **code quality**, **testing**, **documentation**, and **architecture**. The architecture is redesigned with a pipeline/middleware pattern and event hooks. Breaking changes to the public API are allowed for cleaner design.

## Constraints

- **Package structure**: Remains `hother/streamblocks` (no flattening)
- **Breaking changes allowed**: API can be redesigned for cleaner architecture
- **Full redesign**: Extract components, add middleware pipeline, add event hooks

---

## Phase 1: Code Quality (PRs 1.1-1.3)

### PR 1.1: Replace bare `except Exception` in syntaxes

**Files:**
- `src/hother/streamblocks/syntaxes/delimiter.py` (lines 119, 128, 209, 232, 247, 255)
- `src/hother/streamblocks/syntaxes/markdown.py` (lines 103, 127, 146, 155)

**Changes:**
```python
# Before
except Exception as e:
    return ParseResult(success=False, error=str(e))

# After - use specific exceptions
except yaml.YAMLError as e:
    return ParseResult(success=False, error=f"YAML error: {e}")
except pydantic.ValidationError as e:
    return ParseResult(success=False, error=f"Validation error: {e}")
except (ValueError, TypeError, KeyError) as e:
    return ParseResult(success=False, error=f"Parse error: {e}")
```

### PR 1.2: Add `__repr__` to BlockCandidate

**File:** `src/hother/streamblocks/core/models.py`

```python
def __repr__(self) -> str:
    return (
        f"BlockCandidate(syntax={type(self.syntax).__name__}, "
        f"start_line={self.start_line}, state={self.state}, "
        f"lines={len(self.lines)}, section={self.current_section})"
    )
```

### PR 1.3: Use TypeGuard in blocks/files.py

**File:** `src/hother/streamblocks/blocks/files.py`

```python
from typing import TypeGuard, Literal

ActionLiteral = Literal["create", "edit", "delete"]

def is_valid_action(action: str) -> TypeGuard[ActionLiteral]:
    return action in ("create", "edit", "delete")
```

---

## Phase 2: Testing Infrastructure (PRs 2.1-2.3)

### PR 2.1: Create `tests/conftest.py`

```python
import pytest
from hother.streamblocks import (
    Registry, StreamBlockProcessor, DelimiterPreambleSyntax
)
from hother.streamblocks.blocks import FileOperations

@pytest.fixture
def delimiter_preamble_syntax():
    return DelimiterPreambleSyntax()

@pytest.fixture
def file_operations_registry(delimiter_preamble_syntax):
    registry = Registry(syntax=delimiter_preamble_syntax)
    registry.register("files_operations", FileOperations)
    return registry

@pytest.fixture
def processor(file_operations_registry):
    return StreamBlockProcessor(file_operations_registry)

@pytest.fixture
def mock_stream():
    async def _create(text: str):
        for line in text.split("\n"):
            yield line + "\n"
    return _create
```

### PR 2.2: Add state machine transition tests

**File:** `tests/test_state_machine.py`

```python
import pytest
from hother.streamblocks.core.pipeline.line_accumulator import LineAccumulator, LineOutput
from hother.streamblocks.core.pipeline.block_state_machine import (
    BlockStateMachine, StateMachineEvent, StateMachineEventType
)
from hother.streamblocks import DelimiterPreambleSyntax


class TestLineAccumulator:
    """Tests for LineAccumulator component."""

    def test_single_complete_line(self):
        acc = LineAccumulator()
        result = list(acc.process("Hello\n"))
        assert len(result) == 1
        assert result[0].line == "Hello"
        assert result[0].line_number == 1
        assert result[0].is_partial is False

    def test_incomplete_line_buffered(self):
        acc = LineAccumulator()
        assert list(acc.process("Hel")) == []
        result = list(acc.process("lo\n"))
        assert result[0].line == "Hello"

    def test_multiple_lines_in_chunk(self):
        acc = LineAccumulator()
        result = list(acc.process("Line1\nLine2\nLine3\n"))
        assert len(result) == 3
        assert [r.line for r in result] == ["Line1", "Line2", "Line3"]

    def test_finalize_flushes_buffer(self):
        acc = LineAccumulator()
        list(acc.process("incomplete"))
        result = list(acc.finalize())
        assert len(result) == 1
        assert result[0].line == "incomplete"

    def test_max_line_length_truncation(self):
        acc = LineAccumulator(max_line_length=10)
        result = list(acc.process("This is a very long line\n"))
        assert result[0].line == "This is a "
        assert result[0].is_partial is True

    def test_line_numbers_increment(self):
        acc = LineAccumulator()
        list(acc.process("a\nb\n"))
        result = list(acc.process("c\n"))
        assert result[0].line_number == 3

    def test_reset_clears_state(self):
        acc = LineAccumulator()
        list(acc.process("partial"))
        acc.reset()
        assert acc.current_line_number == 0
        assert acc.has_pending is False

    def test_empty_string_no_output(self):
        acc = LineAccumulator()
        assert list(acc.process("")) == []


class TestBlockStateMachine:
    """Tests for BlockStateMachine state transitions."""

    @pytest.fixture
    def state_machine(self):
        return BlockStateMachine(DelimiterPreambleSyntax())

    def test_raw_line_outside_block(self, state_machine):
        events = list(state_machine.process(LineOutput("plain text", 1)))
        assert len(events) == 1
        assert events[0].type == StateMachineEventType.RAW_LINE

    def test_block_opening_detected(self, state_machine):
        events = list(state_machine.process(LineOutput("!!id:type", 1)))
        assert len(events) == 1
        assert events[0].type == StateMachineEventType.BLOCK_OPENED
        assert events[0].candidate is not None

    def test_block_line_inside_block(self, state_machine):
        list(state_machine.process(LineOutput("!!id:type", 1)))
        events = list(state_machine.process(LineOutput("content", 2)))
        assert events[0].type == StateMachineEventType.BLOCK_LINE

    def test_block_closing_detected(self, state_machine):
        list(state_machine.process(LineOutput("!!id:type", 1)))
        list(state_machine.process(LineOutput("content", 2)))
        events = list(state_machine.process(LineOutput("!!end", 3)))
        assert events[0].type == StateMachineEventType.BLOCK_CLOSED

    def test_unclosed_block_on_finalize(self, state_machine):
        list(state_machine.process(LineOutput("!!id:type", 1)))
        events = list(state_machine.finalize())
        assert len(events) == 1
        assert events[0].type == StateMachineEventType.BLOCK_UNCLOSED

    def test_block_size_exceeded(self):
        sm = BlockStateMachine(DelimiterPreambleSyntax(), max_block_size=50)
        list(sm.process(LineOutput("!!id:type", 1)))
        events = list(sm.process(LineOutput("x" * 100, 2)))
        assert any(e.type == StateMachineEventType.BLOCK_SIZE_EXCEEDED for e in events)

    def test_is_inside_block_property(self, state_machine):
        assert state_machine.is_inside_block is False
        list(state_machine.process(LineOutput("!!id:type", 1)))
        assert state_machine.is_inside_block is True

    def test_active_candidates_property(self, state_machine):
        assert state_machine.active_candidates == []
        list(state_machine.process(LineOutput("!!id:type", 1)))
        assert len(state_machine.active_candidates) == 1


class TestStateMachineIntegration:
    """Integration tests for full pipeline flow."""

    def test_complete_block_flow(self):
        syntax = DelimiterPreambleSyntax()
        acc = LineAccumulator()
        sm = BlockStateMachine(syntax)

        text = "!!block01:files_operations\nsrc/main.py:C\n!!end\n"
        event_types = []

        for line_out in acc.process(text):
            for sm_event in sm.process(line_out):
                event_types.append(sm_event.type)

        assert StateMachineEventType.BLOCK_OPENED in event_types
        assert StateMachineEventType.BLOCK_LINE in event_types
        assert StateMachineEventType.BLOCK_CLOSED in event_types

    def test_mixed_raw_and_block_lines(self):
        syntax = DelimiterPreambleSyntax()
        acc = LineAccumulator()
        sm = BlockStateMachine(syntax)

        text = "raw line\n!!id:type\ncontent\n!!end\nanother raw\n"
        event_types = []

        for line_out in acc.process(text):
            for sm_event in sm.process(line_out):
                event_types.append(sm_event.type)

        assert event_types.count(StateMachineEventType.RAW_LINE) == 2
        assert event_types.count(StateMachineEventType.BLOCK_OPENED) == 1
```

### PR 2.3: Add edge case tests

**File:** `tests/test_edge_cases.py`

```python
import pytest
from hother.streamblocks import (
    StreamBlockProcessor, Registry, DelimiterPreambleSyntax,
    EventType, BlockExtractedEvent, BlockRejectedEvent
)
from hother.streamblocks.blocks import FileOperations


class TestBufferLimits:
    """Tests for buffer and size limit handling."""

    @pytest.fixture
    def processor(self):
        syntax = DelimiterPreambleSyntax()
        registry = Registry(syntax=syntax)
        registry.register("files_operations", FileOperations)
        config = ProcessorConfig(max_line_length=100, max_block_size=500)
        return StreamBlockProcessor(registry, config=config)

    async def test_line_truncation_still_parses(self, processor):
        stream = self._make_stream([
            "!!id:files_operations\n",
            "src/file.py:C\n",
            "!!end\n"
        ])
        events = [e async for e in processor.process_stream(stream)]
        extracted = [e for e in events if isinstance(e, BlockExtractedEvent)]
        assert len(extracted) == 1

    async def test_block_rejected_on_size_exceeded(self, processor):
        content = "x" * 600
        stream = self._make_stream([
            "!!id:files_operations\n",
            f"{content}:C\n",
            "!!end\n"
        ])
        events = [e async for e in processor.process_stream(stream)]
        rejected = [e for e in events if isinstance(e, BlockRejectedEvent)]
        assert len(rejected) == 1
        assert "size" in rejected[0].reason.lower()

    @staticmethod
    async def _make_stream(lines):
        for line in lines:
            yield line


class TestEmptyAndMalformedInput:
    """Tests for edge cases with empty or malformed input."""

    @pytest.fixture
    def processor(self):
        syntax = DelimiterPreambleSyntax()
        registry = Registry(syntax=syntax)
        registry.register("files_operations", FileOperations)
        return StreamBlockProcessor(registry)

    async def test_empty_stream(self, processor):
        async def empty_stream():
            return
            yield

        events = [e async for e in processor.process_stream(empty_stream())]
        assert len(events) == 0

    async def test_stream_with_only_whitespace(self, processor):
        async def whitespace_stream():
            yield "   \n"
            yield "\t\n"
            yield "\n"

        events = [e async for e in processor.process_stream(whitespace_stream())]
        raw_events = [e for e in events if e.type == EventType.RAW_TEXT]
        assert len(raw_events) == 3

    async def test_unclosed_block_at_stream_end(self, processor):
        async def unclosed_stream():
            yield "!!id:files_operations\n"
            yield "content:C\n"

        events = [e async for e in processor.process_stream(unclosed_stream())]
        rejected = [e for e in events if isinstance(e, BlockRejectedEvent)]
        assert len(rejected) == 1
        assert "closing" in rejected[0].reason.lower()

    async def test_invalid_block_type(self, processor):
        async def invalid_type_stream():
            yield "!!id:unknown_type\n"
            yield "content\n"
            yield "!!end\n"

        events = [e async for e in processor.process_stream(invalid_type_stream())]
        rejected = [e for e in events if isinstance(e, BlockRejectedEvent)]
        assert len(rejected) == 1

    async def test_block_immediately_closed(self, processor):
        async def immediate_close():
            yield "!!id:files_operations\n"
            yield "!!end\n"

        events = [e async for e in processor.process_stream(immediate_close())]
        block_events = [e for e in events if e.type in (
            EventType.BLOCK_EXTRACTED, EventType.BLOCK_REJECTED
        )]
        assert len(block_events) == 1


class TestHookEdgeCases:
    """Tests for hook system edge cases."""

    @pytest.fixture
    def processor(self):
        syntax = DelimiterPreambleSyntax()
        registry = Registry(syntax=syntax)
        registry.register("files_operations", FileOperations)
        return StreamBlockProcessor(registry)

    async def test_hook_exception_doesnt_break_processing(self, processor):
        def bad_hook(event, phase, context):
            raise ValueError("Hook error!")

        processor.add_hook(bad_hook, name="bad_hook")

        async def stream():
            yield "!!id:files_operations\n"
            yield "src/file.py:C\n"
            yield "!!end\n"

        events = [e async for e in processor.process_stream(stream())]
        extracted = [e for e in events if isinstance(e, BlockExtractedEvent)]
        assert len(extracted) == 1

    async def test_disabled_hook_not_called(self, processor):
        call_count = 0

        def counting_hook(event, phase, context):
            nonlocal call_count
            call_count += 1
            return None

        processor.add_hook(counting_hook, name="counter")
        processor.hooks.disable("counter")

        async def stream():
            yield "text\n"

        [e async for e in processor.process_stream(stream())]
        assert call_count == 0

    def test_hook_priority_ordering(self, processor):
        order = []

        def hook_a(event, phase, context):
            order.append("a")
            return None

        def hook_b(event, phase, context):
            order.append("b")
            return None

        processor.add_hook(hook_a, name="a", priority=200)
        processor.add_hook(hook_b, name="b", priority=100)

        processor.process_chunk("text\n")

        assert order.index("b") < order.index("a")
```

---

## Phase 3: Documentation (PRs 3.1-3.2)

### PR 3.1: Create ARCHITECTURE.md

Include:
- State machine diagram (Mermaid)
- Event flow documentation
- Component responsibilities
- Extension points

### PR 3.2: Document sync vs async API

Add to docs explaining `process_stream()` vs `process_chunk()` + `finalize()` patterns.

---

## Phase 4: Architecture Refactoring (PRs 4.1-4.6)

### PR 4.1: Create pipeline module structure

**New directory:** `src/hother/streamblocks/core/pipeline/`

```
pipeline/
├── __init__.py
├── base.py           # PipelineStage protocol
├── line_accumulator.py
├── block_state_machine.py
├── block_extractor.py
├── middleware.py
└── pipeline.py       # StreamPipeline orchestrator
```

---

## Detailed Pipeline Architecture

### PR 4.2: PipelineStage Protocol and LineAccumulator

**File:** `src/hother/streamblocks/core/pipeline/base.py`

```python
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, Generator
from typing import Generic, Protocol, TypeVar

TInput = TypeVar("TInput")
TOutput = TypeVar("TOutput")


class PipelineStage(Protocol[TInput, TOutput]):
    """Protocol for composable pipeline stages."""

    def process(self, input_item: TInput) -> Generator[TOutput, None, None]:
        ...

    async def process_async(self, input_item: TInput) -> AsyncGenerator[TOutput, None]:
        ...

    def finalize(self) -> Generator[TOutput, None, None]:
        ...

    async def finalize_async(self) -> AsyncGenerator[TOutput, None]:
        ...

    def reset(self) -> None:
        ...


class BasePipelineStage(ABC, Generic[TInput, TOutput]):
    """Abstract base class providing default async wrappers."""

    @abstractmethod
    def process(self, input_item: TInput) -> Generator[TOutput, None, None]:
        ...

    async def process_async(self, input_item: TInput) -> AsyncGenerator[TOutput, None]:
        for output in self.process(input_item):
            yield output

    def finalize(self) -> Generator[TOutput, None, None]:
        return
        yield

    async def finalize_async(self) -> AsyncGenerator[TOutput, None]:
        for output in self.finalize():
            yield output

    def reset(self) -> None:
        pass
```

**File:** `src/hother/streamblocks/core/pipeline/line_accumulator.py`

```python
from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass

from hother.streamblocks.core.pipeline.base import BasePipelineStage


@dataclass(slots=True)
class LineOutput:
    """Output from line accumulator."""
    line: str
    line_number: int
    is_partial: bool = False


class LineAccumulator(BasePipelineStage[str, LineOutput]):
    """Accumulates text chunks and yields complete lines."""

    __slots__ = ("max_line_length", "_buffer", "_line_counter")

    def __init__(self, max_line_length: int = 16_384) -> None:
        self.max_line_length = max_line_length
        self._buffer: list[str] = []
        self._line_counter: int = 0

    def process(self, text: str) -> Generator[LineOutput, None, None]:
        if not text:
            return

        self._buffer.append(text)
        full_text = "".join(self._buffer)
        lines = full_text.split("\n")

        if not full_text.endswith("\n"):
            self._buffer = [lines[-1]]
            lines = lines[:-1]
        else:
            self._buffer = []

        for line in lines:
            self._line_counter += 1
            truncated = len(line) > self.max_line_length
            yield LineOutput(
                line=line[:self.max_line_length] if truncated else line,
                line_number=self._line_counter,
                is_partial=truncated,
            )

    def finalize(self) -> Generator[LineOutput, None, None]:
        if self._buffer:
            final_line = "".join(self._buffer)
            if final_line:
                self._line_counter += 1
                truncated = len(final_line) > self.max_line_length
                yield LineOutput(
                    line=final_line[:self.max_line_length] if truncated else final_line,
                    line_number=self._line_counter,
                    is_partial=truncated,
                )
            self._buffer = []

    def reset(self) -> None:
        self._buffer = []
        self._line_counter = 0

    @property
    def current_line_number(self) -> int:
        return self._line_counter

    @property
    def has_pending(self) -> bool:
        return bool(self._buffer)
```

### PR 4.3: BlockStateMachine

**File:** `src/hother/streamblocks/core/pipeline/block_state_machine.py`

```python
from __future__ import annotations

from collections import deque
from collections.abc import Generator
from dataclasses import dataclass
from enum import StrEnum, auto
from typing import TYPE_CHECKING, Any

from hother.streamblocks.core.models import BlockCandidate
from hother.streamblocks.core.pipeline.base import BasePipelineStage
from hother.streamblocks.core.pipeline.line_accumulator import LineOutput
from hother.streamblocks.core.types import BlockState

if TYPE_CHECKING:
    from hother.streamblocks.syntaxes.base import BaseSyntax


class StateMachineEventType(StrEnum):
    """Internal event types emitted by the state machine."""
    RAW_LINE = auto()
    BLOCK_OPENED = auto()
    BLOCK_LINE = auto()
    BLOCK_CLOSED = auto()
    BLOCK_UNCLOSED = auto()
    BLOCK_SIZE_EXCEEDED = auto()


@dataclass(slots=True)
class StateMachineEvent:
    """Event emitted by BlockStateMachine."""
    type: StateMachineEventType
    line: str
    line_number: int
    candidate: BlockCandidate | None = None
    section: str | None = None
    inline_metadata: dict[str, Any] | None = None


class BlockStateMachine(BasePipelineStage[LineOutput, StateMachineEvent]):
    """State machine for tracking block detection across lines."""

    __slots__ = ("syntax", "lines_buffer", "max_block_size", "_buffer", "_candidates")

    def __init__(
        self,
        syntax: BaseSyntax,
        *,
        lines_buffer: int = 5,
        max_block_size: int = 1_048_576,
    ) -> None:
        self.syntax = syntax
        self.lines_buffer = lines_buffer
        self.max_block_size = max_block_size
        self._buffer: deque[str] = deque(maxlen=lines_buffer)
        self._candidates: list[BlockCandidate] = []

    # ... (full implementation in plan file)

    @property
    def active_candidates(self) -> list[BlockCandidate]:
        return list(self._candidates)

    @property
    def is_inside_block(self) -> bool:
        return len(self._candidates) > 0
```

### PR 4.4: BlockExtractor and Middleware

See full implementation in the detailed plan file.

### PR 4.5: Event Hook System

**File:** `src/hother/streamblocks/core/hooks.py`

```python
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum, auto
from typing import Any, Awaitable, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field


class HookPhase(StrEnum):
    """Phase in processing where hooks execute."""
    PRE_EMIT = auto()
    POST_EMIT = auto()


class HookAction(StrEnum):
    """Action a hook can return."""
    EMIT = auto()
    SUPPRESS = auto()


class HookContext(BaseModel):
    """Context passed to hooks with processing state."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    line_number: int = 0
    total_events_emitted: int = 0
    blocks_extracted: int = 0
    blocks_rejected: int = 0
    stream_started_at: float | None = None
    user_data: dict[str, Any] = Field(default_factory=dict)
    chain_data: dict[str, Any] = Field(default_factory=dict)


class HookResult(BaseModel):
    """Result returned from a hook."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    action: HookAction = HookAction.EMIT
    event: Any | None = None
    inject_events: list[Any] = Field(default_factory=list)
    chain_data: dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class EventHook(Protocol):
    """Protocol for event hooks."""

    def __call__(
        self,
        event: Any,
        phase: HookPhase,
        context: HookContext,
    ) -> HookResult | None | Awaitable[HookResult | None]:
        ...


@dataclass
class HookRegistration:
    """Registration info for a hook."""
    hook: EventHook
    name: str
    priority: int = 100
    phases: set[HookPhase] = field(default_factory=lambda: {HookPhase.PRE_EMIT})
    event_types: set[Any] | None = None
    enabled: bool = True


class HookRegistry:
    """Registry for managing event hooks."""
    # ... (full implementation in plan file)
```

---

## Hook Use Cases (User Examples)

Hooks provide extension points to observe, transform, or filter events **without modifying the core pipeline**. They execute at two phases:
- **PRE_EMIT**: Before event is yielded (can transform or suppress)
- **POST_EMIT**: After event is yielded (observation only)

### Use Case 1: Logging - Log all events

```python
import structlog
from hother.streamblocks import StreamPipeline
from hother.streamblocks.hooks import create_logging_hook
from hother.streamblocks.core.hooks import HookPhase

logger = structlog.get_logger()
pipeline = StreamPipeline(registry)

pipeline.add_hook(
    create_logging_hook(logger),
    name="logger",
    phases={HookPhase.POST_EMIT},
)

# Output: event_emitted event_type=BLOCK_EXTRACTED line=15 total=13
```

### Use Case 2: Metrics - Collect processing stats

```python
from hother.streamblocks.hooks import MetricsHook

metrics = MetricsHook()
pipeline.add_hook(metrics, name="metrics", phases={HookPhase.POST_EMIT})

async for event in pipeline.process(stream):
    ...

print(metrics.summary)
# {
#     "event_counts": {"BLOCK_EXTRACTED": 5, "RAW_TEXT": 42},
#     "block_types": {"files_operations": 3, "patch": 2},
#     "duration_seconds": 2.5,
#     "events_per_second": 52.8
# }
```

### Use Case 3: Security Filter - Block dangerous operations

```python
from hother.streamblocks.hooks import create_block_filter

pipeline.add_hook(
    create_block_filter(
        allowed_types={"files_operations", "patch"},
        blocked_types={"shell_command"},  # Never execute!
    ),
    name="security_filter",
    priority=10,  # Run early
)
```

### Use Case 4: Human-in-the-Loop - Require approval

```python
from hother.streamblocks.hooks import create_approval_hook

async def require_user_approval(block):
    if block.metadata.block_type == "files_operations":
        for file in block.content.files:
            print(f"  {file.action}: {file.path}")
        response = input("Approve? [y/N] ")
        return response.lower() == "y"
    return True

pipeline.add_hook(
    create_approval_hook(require_user_approval, rejection_reason="User rejected"),
    name="approval",
)
```

### Use Case 5: Transform - Add metadata to events

```python
def add_timestamp(event, phase, context):
    if event.type == EventType.BLOCK_EXTRACTED:
        modified = event.model_copy(deep=True)
        modified.block.content.timestamp = time.time()
        return HookResult(event=modified)
    return None

pipeline.add_hook(add_timestamp, name="timestamp", phases={HookPhase.PRE_EMIT})
```

### Use Case 6: Audit Trail - Inject additional events

```python
def audit_hook(event, phase, context):
    if event.type == EventType.BLOCK_EXTRACTED:
        if event.block.metadata.block_type == "files_operations":
            audit_event = RawTextEvent(
                data=f"[AUDIT] File operation by {context.user_data.get('user')}"
            )
            return HookResult(inject_events=[audit_event])
    return None

pipeline.add_hook(audit_hook, name="audit")
```

### Hook Priority and Management

```python
# Priority ordering (lower = earlier)
pipeline.add_hook(security_filter, priority=10)   # First
pipeline.add_hook(transform_hook, priority=50)    # Second
pipeline.add_hook(logging_hook, priority=200)     # Last

# Enable/disable without removing
pipeline.hooks.disable("logger")
pipeline.hooks.enable("logger")

# Unregister completely
pipeline.hooks.unregister("approval")
```

---

### PR 4.6: Replace StreamBlockProcessor with StreamPipeline

Since backward compatibility is not required, we replace `StreamBlockProcessor` entirely with a cleaner `StreamPipeline` class. The old processor.py file is deleted and replaced with the pipeline-based design.

**Delete:** `src/hother/streamblocks/core/processor.py` (old 770-line file)

**New file:** `src/hother/streamblocks/core/pipeline/pipeline.py`

See full implementation in the detailed plan file.

---

## Execution Order & Dependencies

```
Phase 1 (parallel)          Phase 2 (parallel)         Phase 3 (parallel)
├── PR 1.1 exceptions       ├── PR 2.1 conftest        ├── PR 3.1 ARCHITECTURE.md
├── PR 1.2 __repr__         ├── PR 2.2 state tests     └── PR 3.2 sync/async docs
└── PR 1.3 TypeGuard        └── PR 2.3 edge tests
                                      │
                                      ▼
                            Phase 4 (sequential)
                            ├── PR 4.1 pipeline structure
                            ├── PR 4.2 LineAccumulator
                            ├── PR 4.3 BlockStateMachine
                            ├── PR 4.4 BlockExtractor + Middleware
                            ├── PR 4.5 Hook system
                            └── PR 4.6 Processor refactor
```

---

## Validation Commands (per PR)

```bash
uv run lefthook run pre-commit --all-files -- --no-stash
uv run pytest tests/ -v
uv run python examples/run_examples.py --skip-api
```

---

## Critical Files

| File | Changes |
|------|---------|
| `core/processor.py` | **DELETE** - replaced by pipeline (PR 4.6) |
| `core/pipeline/pipeline.py` | New main entry point `StreamPipeline` (PR 4.6) |
| `core/pipeline/base.py` | PipelineStage protocol (PR 4.2) |
| `core/pipeline/line_accumulator.py` | LineAccumulator component (PR 4.2) |
| `core/pipeline/block_state_machine.py` | BlockStateMachine component (PR 4.3) |
| `core/pipeline/block_extractor.py` | BlockExtractor component (PR 4.4) |
| `core/pipeline/middleware.py` | Middleware system (PR 4.4) |
| `core/hooks.py` | Hook system (PR 4.5) |
| `hooks/__init__.py` | Pre-built hooks (PR 4.5) |
| `__init__.py` | Update exports: remove `StreamBlockProcessor`, add `StreamPipeline` |
| `syntaxes/delimiter.py` | Exception handling (PR 1.1) |
| `syntaxes/markdown.py` | Exception handling (PR 1.1) |
| `core/models.py` | Add `__repr__` (PR 1.2) |
| `blocks/files.py` | TypeGuard (PR 1.3) |
| `tests/conftest.py` | New fixtures (PR 2.1) |

---

## New Public API (Breaking Changes)

**Removed:**
- `StreamBlockProcessor` - replaced by `StreamPipeline`

**New main API:**
```python
from hother.streamblocks import StreamPipeline, Registry

# Create pipeline (replaces StreamBlockProcessor)
pipeline = StreamPipeline(registry)

# Process stream (same pattern, different class name)
async for event in pipeline.process(stream):
    if isinstance(event, BlockExtractedEvent):
        print(event.block.metadata.id)

# Add hooks
pipeline.add_hook(my_hook, name="logger", phases={HookPhase.POST_EMIT})

# Use pre-built hooks
from hother.streamblocks.hooks import MetricsHook, create_block_filter
metrics = MetricsHook()
pipeline.add_hook(metrics, name="metrics")

# Access hook registry
pipeline.hooks.disable("logger")

# Use pipeline components standalone
from hother.streamblocks.core.pipeline import LineAccumulator, BlockStateMachine

acc = LineAccumulator(max_line_length=1000)
for line in acc.process("Hello\nWorld\n"):
    print(line)
```

**Migration guide:**
```python
# Before (old API)
processor = StreamBlockProcessor(registry)
async for event in processor.process_stream(stream):
    ...

# After (new API)
pipeline = StreamPipeline(registry)
async for event in pipeline.process(stream):
    ...
```
