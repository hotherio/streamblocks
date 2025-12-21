"""Agent-specific events for UI integration.

These events are emitted during agent execution to allow
real-time UI updates. They complement StreamBlocks' native
events (TextDeltaEvent, BlockExtractedEvent, etc.).

Note: Natural text is already visible via TextDeltaEvent -
no separate ThoughtEvent is needed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from examples.agent.executor import ToolResult


@dataclass
class ToolCallEvent:
    """Emitted when a tool call block is detected.

    This event fires immediately when the ToolCall block is extracted,
    before tool execution begins.

    Attributes:
        tool_name: Name of the tool to be called
        tool_id: Unique ID of this tool call (from block metadata)
        parameters: Parameters extracted from the block
    """

    tool_name: str
    tool_id: str
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolStartedEvent:
    """Emitted when tool execution starts in the background.

    With speculative continuation, the LLM continues streaming
    while the tool executes. This event marks the start of
    background execution.

    Attributes:
        tool_name: Name of the tool being executed
        tool_id: Unique ID of this tool call
    """

    tool_name: str
    tool_id: str


@dataclass
class ToolCallResultEvent:
    """Emitted when a tool result is available.

    This event fires when a tool completes execution,
    regardless of success or failure.

    Attributes:
        tool_name: Name of the tool that completed
        tool_id: Unique ID of this tool call
        result: The ToolResult with success/failure info
        injected: Whether the result was injected mid-stream
    """

    tool_name: str
    tool_id: str
    result: ToolResult
    injected: bool = False  # True if injected while LLM was streaming


@dataclass
class AnswerEvent:
    """Emitted when the agent produces a final answer.

    This event fires when a FinalAnswer block is extracted,
    signaling the end of the agent's execution.

    Attributes:
        answer: The final answer text
        tools_called: Total number of tools called
        total_time: Total execution time in seconds
        llm_calls: Number of LLM API calls made
        total_prompt_tokens: Total input tokens across all calls
        total_completion_tokens: Total output tokens across all calls
        total_tokens: Total tokens (includes cached + thoughts if applicable)
        total_cached_tokens: Total tokens from cached content
        total_thoughts_tokens: Total thinking tokens (Gemini 2.5+ thinking models)
    """

    answer: str
    tools_called: int = 0
    total_time: float = 0.0
    llm_calls: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    total_cached_tokens: int = 0
    total_thoughts_tokens: int = 0


@dataclass
class LLMCallStartEvent:
    """Emitted when an LLM API call starts.

    Attributes:
        call_number: Sequential number of this LLM call (1-indexed)
        timestamp: Time when the call started (time.time())
    """

    call_number: int
    timestamp: float


@dataclass
class LLMFirstTokenEvent:
    """Emitted when the first token arrives from an LLM call.

    Attributes:
        call_number: Sequential number of this LLM call
        ttft: Time to first token in seconds
    """

    call_number: int
    ttft: float


@dataclass
class LLMCallEndEvent:
    """Emitted when an LLM call completes (naturally or cancelled).

    Attributes:
        call_number: Sequential number of this LLM call
        prompt_tokens: Number of input tokens
        completion_tokens: Number of output tokens
        total_tokens: Total tokens (includes cached + thoughts if applicable)
        cached_tokens: Number of tokens from cached content
        thoughts_tokens: Number of thinking tokens (Gemini 2.5+ thinking models)
        duration: Total call duration in seconds
        cancelled: Whether the stream was cancelled mid-generation
    """

    call_number: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cached_tokens: int = 0
    thoughts_tokens: int = 0
    duration: float = 0.0
    cancelled: bool = False


@dataclass
class StreamCancelledEvent:
    """Emitted when the LLM stream is cancelled to inject tool results.

    This is a key event in speculative continuation - it indicates
    that the LLM was still generating when a tool completed, so
    we cancelled the stream to inject results.

    Attributes:
        reason: Why the stream was cancelled
        accumulated_text: Text generated before cancellation (may be discarded)
    """

    reason: str
    accumulated_text: str = ""
