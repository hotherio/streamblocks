"""Main Agent class with decorator-based tool registration.

Provides a Pydantic AI-compatible API for building agents with StreamBlocks.

Example:
    agent = Agent(model="gemini-2.5-flash")

    @agent.tool
    def calculate(expression: str) -> float:
        '''Evaluate a math expression.'''
        return eval(expression)

    result = await agent.run("What is 25 * 4?")
    print(result.answer)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from google import genai  # type: ignore[import-not-found]

from examples.agent.context import RunContext
from examples.agent.events import AnswerEvent
from examples.agent.executor import ToolExecutor
from examples.agent.speculative_stream import SpeculativeAgentStream

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Callable


@dataclass
class AgentResult:
    """Result from agent execution.

    Attributes:
        answer: The final answer text
        success: Whether the agent completed successfully
        tools_called: Number of tools called
        iterations: Number of LLM calls made
    """

    answer: str
    success: bool = True
    tools_called: int = 0
    iterations: int = 0


class Agent[TDeps]:
    """ReAct agent with speculative continuation.

    Key Features:
    - Decorator-based tool registration (@agent.tool)
    - Pydantic AI-style dependency injection (RunContext)
    - Speculative continuation: LLM streams while tools execute in parallel
    - Smart result injection based on stream state

    Example:
        agent = Agent(model="gemini-2.5-flash")

        @agent.tool
        def calculate(expression: str) -> float:
            '''Evaluate a math expression.'''
            return eval(expression)

        @agent.tool_plain
        async def search(query: str) -> list[str]:
            '''Search for information.'''
            return ["result1", "result2"]

        # With dependencies
        @dataclass
        class AppDeps:
            api_key: str

        agent = Agent[AppDeps](model="gemini-2.5-flash")

        @agent.tool
        def fetch_data(ctx: RunContext[AppDeps], url: str) -> dict:
            # Access ctx.deps.api_key
            ...

        result = await agent.run("...", deps=AppDeps(api_key="..."))
    """

    def __init__(
        self,
        model: str = "gemini-2.5-pro",
        *,
        api_key: str | None = None,
        max_iterations: int = 10,
    ) -> None:
        """Initialize the agent.

        Args:
            model: Model ID to use
            api_key: API key (defaults to GEMINI_API_KEY or GOOGLE_API_KEY env var)
            max_iterations: Maximum number of LLM calls
        """
        self.model = model
        self.max_iterations = max_iterations

        # Initialize Gemini client
        api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            msg = "API key required. Set GEMINI_API_KEY or GOOGLE_API_KEY env var."
            raise ValueError(msg)

        self.client = genai.Client(api_key=api_key)

        # Tool executor
        self.executor = ToolExecutor()

    def tool(
        self,
        func: Callable[..., Any] | None = None,
        *,
        name: str | None = None,
        description: str | None = None,
        timeout: float = 30.0,
        retries: int = 0,
    ) -> Callable[..., Any]:
        """Register a tool that receives RunContext.

        The first parameter should be RunContext[TDeps] for dependency injection.

        Example:
            @agent.tool
            def my_tool(ctx: RunContext[MyDeps], param: str) -> str:
                # Access ctx.deps, ctx.retry, etc.
                return f"Result for {param}"
        """
        return self.executor.register(func, name=name, description=description, timeout=timeout, retries=retries)

    def tool_plain(
        self,
        func: Callable[..., Any] | None = None,
        *,
        name: str | None = None,
        description: str | None = None,
        timeout: float = 30.0,
        retries: int = 0,
    ) -> Callable[..., Any]:
        """Register a plain tool (no RunContext).

        Use this for tools that don't need dependency injection.

        Example:
            @agent.tool_plain
            def calculate(expression: str) -> float:
                return eval(expression)
        """
        return self.executor.register(func, name=name, description=description, timeout=timeout, retries=retries)

    async def run(self, task: str, *, deps: TDeps | None = None) -> AgentResult:
        """Run the agent on a task.

        Args:
            task: The task/question to answer
            deps: Optional dependencies for tools

        Returns:
            AgentResult with the final answer
        """
        # Create context if deps provided
        context: RunContext[Any] | None = None
        if deps is not None:
            context = RunContext(deps=deps)

        # Get tool definitions for system prompt
        tools = [self.executor.get(name) for name in self.executor.list_tools() if self.executor.get(name) is not None]

        # Create speculative stream
        stream = SpeculativeAgentStream(
            client=self.client,
            executor=self.executor,
            tools=tools,  # type: ignore[arg-type]
            model_id=self.model,
            max_iterations=self.max_iterations,
            context=context,
        )

        # Process stream until we get an answer
        answer = ""
        tools_called = 0

        async for event in stream.run(task):
            if isinstance(event, AnswerEvent):
                answer = event.answer
                tools_called = event.tools_called
                break

        return AgentResult(
            answer=answer,
            success=bool(answer),
            tools_called=tools_called,
        )

    async def run_stream(self, task: str, *, deps: TDeps | None = None) -> AsyncIterator[Any]:
        """Run the agent on a task, yielding all events.

        Use this for real-time UI updates.

        Args:
            task: The task/question to answer
            deps: Optional dependencies for tools

        Yields:
            Various events: TextDeltaEvent, ToolCallEvent, ToolStartedEvent,
            ToolCallResultEvent, StreamCancelledEvent, AnswerEvent
        """
        # Create context if deps provided
        context: RunContext[Any] | None = None
        if deps is not None:
            context = RunContext(deps=deps)

        # Get tool definitions for system prompt
        tools = [self.executor.get(name) for name in self.executor.list_tools() if self.executor.get(name) is not None]

        # Create speculative stream
        stream = SpeculativeAgentStream(
            client=self.client,
            executor=self.executor,
            tools=tools,  # type: ignore[arg-type]
            model_id=self.model,
            max_iterations=self.max_iterations,
            context=context,
        )

        # Yield all events
        async for event in stream.run(task):
            yield event
