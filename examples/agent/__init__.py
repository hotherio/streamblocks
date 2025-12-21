"""StreamBlocks Agent - ReAct agent with speculative continuation.

This module demonstrates how StreamBlocks can emulate function calling
with parallel tool execution while the LLM continues streaming.

Key Features:
- Decorator-based tool registration (@agent.tool)
- Pydantic AI-style dependency injection (RunContext)
- Speculative continuation: LLM streams while tools execute in parallel
- Smart result injection: cancel+resume or new call based on stream state
"""

from examples.agent.agent import Agent
from examples.agent.blocks import FinalAnswer, ToolCall, ToolCallContent, ToolCallMetadata
from examples.agent.context import RunContext
from examples.agent.events import (
    AnswerEvent,
    ToolCallEvent,
    ToolCallResultEvent,
    ToolStartedEvent,
)
from examples.agent.executor import ToolExecutor, ToolResult

__all__ = [
    "Agent",
    "AnswerEvent",
    "FinalAnswer",
    "RunContext",
    "ToolCall",
    "ToolCallContent",
    "ToolCallEvent",
    "ToolCallMetadata",
    "ToolCallResultEvent",
    "ToolExecutor",
    "ToolResult",
    "ToolStartedEvent",
]
