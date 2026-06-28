"""Thinking Agent Stream - Dynamic thinking mode control.

This module implements speculative continuation with dynamic thinking:
- First LLM call uses thinking mode (thinking_budget=128)
- Subsequent calls after tool injection use NO thinking (thinking_budget=0)

This demonstrates the flexibility of controlling model behavior per-call.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from typing import TYPE_CHECKING, Any

# Add parent directory to path for imports when run standalone
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from google.genai.types import GenerateContentConfig, ThinkingConfig

from examples.agent.blocks import FinalAnswer, ToolCall, Wait
from examples.agent.events import (
    AnswerEvent,
    LLMCallEndEvent,
    LLMCallStartEvent,
    LLMFirstTokenEvent,
    StreamCancelledEvent,
    ToolCallEvent,
    ToolCallResultEvent,
    ToolStartedEvent,
)
from examples.agent.prompts import build_system_prompt, format_tool_result
from hother.streamblocks import (
    BlockExtractedEvent,
    DelimiterFrontmatterSyntax,
    Registry,
    StreamBlockProcessor,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from examples.agent.context import RunContext
    from examples.agent.executor import ToolDefinition, ToolExecutor, ToolResult


class ThinkingAgentStream:
    """Stream controller with dynamic thinking mode.

    Key Features:
    - First call uses thinking mode (better reasoning for complex tasks)
    - Subsequent calls disable thinking (faster response after feedback)
    - Tools execute in background while LLM continues streaming
    - Results are injected as soon as available

    Usage:
        stream = ThinkingAgentStream(client, executor, tools)
        async for event in stream.run("What is 2+2?"):
            if isinstance(event, AnswerEvent):
                print(f"Answer: {event.answer}")
    """

    def __init__(
        self,
        client: Any,
        executor: ToolExecutor,
        tools: list[ToolDefinition],
        model_id: str = "gemini-2.5-flash",
        max_iterations: int = 10,
        context: RunContext[Any] | None = None,
        first_call_thinking_budget: int = 128,
        subsequent_thinking_budget: int = 0,
    ) -> None:
        """Initialize the thinking stream.

        Args:
            client: Gemini client instance
            executor: Tool executor with registered tools
            tools: List of tool definitions (for system prompt)
            model_id: Model to use
            max_iterations: Maximum number of LLM calls
            context: Optional RunContext for dependency injection
            first_call_thinking_budget: Thinking budget for first LLM call
            subsequent_thinking_budget: Thinking budget for subsequent calls
        """
        self.client = client
        self.executor = executor
        self.tools = tools
        self.model_id = model_id
        self.max_iterations = max_iterations
        self.context = context
        self.first_call_thinking_budget = first_call_thinking_budget
        self.subsequent_thinking_budget = subsequent_thinking_budget

        # Build system prompt
        self.system_prompt = build_system_prompt(tools)

        # Conversation history (managed manually since we create new chats)
        self._conversation_history: list[dict[str, str]] = []

        # Next message to send
        self._next_message: str | None = None

        # Tool execution state
        self._pending_tools: dict[str, asyncio.Task[ToolResult]] = {}
        self._tool_results: asyncio.Queue[tuple[str, str, ToolResult]] = asyncio.Queue()

        # Stream control
        self._is_streaming = False
        self._done = False
        self._tools_called = 0
        self._tool_call_counter = 0
        self._is_first_call = True  # Track if this is the first LLM call

        # Metrics tracking
        self._llm_call_count = 0
        self._total_prompt_tokens = 0
        self._total_completion_tokens = 0
        self._total_tokens = 0
        self._total_cached_tokens = 0
        self._total_thoughts_tokens = 0
        self._call_metrics: list[dict[str, Any]] = []

        # Setup StreamBlocks registry
        self._syntax = DelimiterFrontmatterSyntax(
            start_delimiter="!!start",
            end_delimiter="!!end",
        )
        self._registry = Registry(syntax=self._syntax)
        self._registry.register("tool_call", ToolCall)
        self._registry.register("final_answer", FinalAnswer)
        self._registry.register("wait", Wait)
        self.processor: StreamBlockProcessor[Any] | None = None

        # Wait mechanism state
        self._awaited_tool_ids: set[str] = set()  # Tool IDs we're waiting for
        self._queued_results: list[tuple[str, str, ToolResult]] = []  # Results waiting to be injected

    def _create_processor(self) -> StreamBlockProcessor[Any]:
        """Create a fresh StreamBlockProcessor for each iteration."""
        return StreamBlockProcessor(self._registry, emit_text_deltas=True)

    def _get_thinking_budget(self) -> int:
        """Get the thinking budget for the current call."""
        if self._is_first_call:
            return self.first_call_thinking_budget
        return self.subsequent_thinking_budget

    async def run(self, task: str) -> AsyncIterator[Any]:
        """Run the agent on a task, yielding events.

        Args:
            task: The task/question to answer

        Yields:
            Various events: TextDeltaEvent, ActionEvent, ToolStartedEvent,
            ObservationEvent, StreamCancelledEvent, AnswerEvent
        """
        # First message is the task
        self._next_message = f"Task: {task}"
        self._conversation_history = []

        iteration = 0
        consecutive_no_progress = 0

        while not self._done and iteration < self.max_iterations:
            iteration += 1
            made_progress = False

            # Stream from LLM with injection support
            async for event in self._stream_with_injection():
                yield event

                # Handle extracted blocks
                if isinstance(event, BlockExtractedEvent):
                    made_progress = True
                    block = event.block
                    block_type = block.metadata.block_type

                    if block_type == "tool_call":
                        self._tool_call_counter += 1
                        tool_name = block.metadata.tool_name  # type: ignore[attr-defined]
                        tool_id = block.metadata.id
                        parameters = block.content.parameters  # type: ignore[attr-defined]

                        yield ToolCallEvent(
                            tool_name=tool_name,
                            tool_id=tool_id,
                            parameters=parameters,
                        )

                        task_obj = asyncio.create_task(self._execute_tool(tool_name, tool_id, parameters))
                        self._pending_tools[tool_id] = task_obj
                        self._tools_called += 1

                        yield ToolStartedEvent(tool_name=tool_name, tool_id=tool_id)

                    elif block_type == "wait":
                        # Wait block - add tool IDs to awaited set
                        tool_ids = block.content.tool_ids  # type: ignore[attr-defined]
                        for tid in tool_ids:
                            if tid in self._pending_tools:
                                self._awaited_tool_ids.add(tid)

                    elif block_type == "final_answer":
                        await self._cancel_pending_tools()
                        self._done = True

                        yield AnswerEvent(
                            answer=block.content.answer,  # type: ignore[attr-defined]
                            tools_called=self._tools_called,
                            llm_calls=self._llm_call_count,
                            total_prompt_tokens=self._total_prompt_tokens,
                            total_completion_tokens=self._total_completion_tokens,
                            total_tokens=self._total_tokens,
                            total_cached_tokens=self._total_cached_tokens,
                            total_thoughts_tokens=self._total_thoughts_tokens,
                        )

                elif isinstance(event, ToolCallResultEvent):
                    made_progress = True

            # Track consecutive iterations without progress
            if made_progress:
                consecutive_no_progress = 0
            else:
                consecutive_no_progress += 1
                if consecutive_no_progress >= 2:
                    self._done = True
                    yield AnswerEvent(
                        answer="Agent did not produce expected block format after multiple attempts.",
                        tools_called=self._tools_called,
                        llm_calls=self._llm_call_count,
                        total_prompt_tokens=self._total_prompt_tokens,
                        total_completion_tokens=self._total_completion_tokens,
                        total_tokens=self._total_tokens,
                        total_cached_tokens=self._total_cached_tokens,
                        total_thoughts_tokens=self._total_thoughts_tokens,
                    )

            # Wait for pending tools if no next message
            if self._next_message is None and not self._done and self._pending_tools:
                if self._pending_tools:
                    _done, _ = await asyncio.wait(
                        list(self._pending_tools.values()),
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                    pending_tool_results: list[str] = []
                    while not self._tool_results.empty():
                        tool_name, tool_id, result = await self._tool_results.get()
                        tool_result_msg = format_tool_result(
                            tool_name,
                            str(result.result) if result.success else str(result.error),
                            result.success,
                        )
                        pending_tool_results.append(tool_result_msg)
                        yield ToolCallResultEvent(
                            tool_name=tool_name,
                            tool_id=tool_id,
                            result=result,
                            injected=False,
                        )
                        made_progress = True
                    if pending_tool_results:
                        self._next_message = "\n\n".join(pending_tool_results)

        if not self._done:
            yield AnswerEvent(
                answer="Max iterations reached without final answer.",
                tools_called=self._tools_called,
                llm_calls=self._llm_call_count,
                total_prompt_tokens=self._total_prompt_tokens,
                total_completion_tokens=self._total_completion_tokens,
                total_tokens=self._total_tokens,
                total_cached_tokens=self._total_cached_tokens,
                total_thoughts_tokens=self._total_thoughts_tokens,
            )

    async def _stream_with_injection(self) -> AsyncIterator[Any]:
        """Stream from LLM, checking for tool results to inject."""
        self._is_streaming = True
        self.processor = self._create_processor()

        message_to_send = self._next_message
        if message_to_send is None:
            self._is_streaming = False
            return

        # Track metrics
        self._llm_call_count += 1
        call_number = self._llm_call_count
        call_start_time = time.time()
        first_token_time: float | None = None
        ttft: float | None = None
        last_usage_metadata: Any = None
        was_cancelled = False

        # Determine thinking budget for this call
        thinking_budget = self._get_thinking_budget()

        # After first call, mark as no longer first
        if self._is_first_call:
            self._is_first_call = False

        yield LLMCallStartEvent(call_number=call_number, timestamp=call_start_time)

        try:
            # Create NEW chat for each call with appropriate thinking config
            # This allows dynamic control of thinking mode
            chat = self.client.aio.chats.create(
                model=self.model_id,
                config=GenerateContentConfig(
                    system_instruction=self.system_prompt,
                    thinking_config=ThinkingConfig(thinking_budget=thinking_budget),
                ),
                history=self._conversation_history,
            )

            response = await chat.send_message_stream(message_to_send)

            accumulated = ""

            async for chunk in response:
                if first_token_time is None:
                    first_token_time = time.time()
                    ttft = first_token_time - call_start_time
                    yield LLMFirstTokenEvent(call_number=call_number, ttft=ttft)

                if hasattr(chunk, "usage_metadata") and chunk.usage_metadata:
                    last_usage_metadata = chunk.usage_metadata

                # Check for completed tools
                while not self._tool_results.empty():
                    tool_name, tool_id, result = await self._tool_results.get()

                    # Check if this is an awaited tool
                    is_awaited = tool_id in self._awaited_tool_ids
                    if is_awaited:
                        self._awaited_tool_ids.discard(tool_id)

                    # Queue the result
                    self._queued_results.append((tool_name, tool_id, result))

                    # Only cancel stream if an awaited tool completed
                    if is_awaited:
                        yield StreamCancelledEvent(
                            reason=f"Awaited tool {tool_name} completed",
                            accumulated_text=accumulated,
                        )

                        was_cancelled = True

                        for end_event in self._emit_call_end_event(
                            call_number, call_start_time, ttft, last_usage_metadata, cancelled=True
                        ):
                            yield end_event

                        # Inject ALL queued results together
                        tool_result_msgs: list[str] = []
                        for q_tool_name, q_tool_id, q_result in self._queued_results:
                            tool_result_msg = format_tool_result(
                                q_tool_name,
                                str(q_result.result) if q_result.success else str(q_result.error),
                                q_result.success,
                            )
                            tool_result_msgs.append(tool_result_msg)

                            yield ToolCallResultEvent(
                                tool_name=q_tool_name,
                                tool_id=q_tool_id,
                                result=q_result,
                                injected=True,
                            )

                        self._queued_results.clear()
                        self._next_message = "\n\n".join(tool_result_msgs)

                        # Update conversation history
                        self._conversation_history.append({"role": "user", "parts": [{"text": message_to_send}]})
                        self._conversation_history.append({"role": "model", "parts": [{"text": accumulated}]})

                        self._is_streaming = False
                        return

                if hasattr(chunk, "text") and chunk.text:
                    accumulated += chunk.text

                async for event in self._process_chunk(chunk):
                    yield event

            # Stream finished - update history
            self._conversation_history.append({"role": "user", "parts": [{"text": message_to_send}]})
            self._conversation_history.append({"role": "model", "parts": [{"text": accumulated}]})

            if not was_cancelled:
                for end_event in self._emit_call_end_event(
                    call_number, call_start_time, ttft, last_usage_metadata, cancelled=False
                ):
                    yield end_event

            if self.processor is not None:
                final_events = self.processor.finalize()
                for event in final_events:
                    yield event

            # Wait for any awaited tools that haven't completed yet
            if self._awaited_tool_ids:
                awaited_tasks = [
                    self._pending_tools[tid]
                    for tid in self._awaited_tool_ids
                    if tid in self._pending_tools
                ]
                if awaited_tasks:
                    await asyncio.gather(*awaited_tasks, return_exceptions=True)

            # Collect any results that came in while waiting
            while not self._tool_results.empty():
                tool_name, tool_id, result = await self._tool_results.get()
                self._awaited_tool_ids.discard(tool_id)
                self._queued_results.append((tool_name, tool_id, result))

            # Process pending tool results (include queued results)
            pending_tool_results: list[str] = []
            pending_events: list[ToolCallResultEvent] = []

            # First, process queued results from await mechanism
            for q_tool_name, q_tool_id, q_result in self._queued_results:
                tool_result_msg = format_tool_result(
                    q_tool_name,
                    str(q_result.result) if q_result.success else str(q_result.error),
                    q_result.success,
                )
                pending_tool_results.append(tool_result_msg)
                pending_events.append(
                    ToolCallResultEvent(
                        tool_name=q_tool_name,
                        tool_id=q_tool_id,
                        result=q_result,
                        injected=False,
                    )
                )
            self._queued_results.clear()

            # Then, process any additional results from the queue
            while not self._tool_results.empty():
                tool_name, tool_id, result = await self._tool_results.get()
                tool_result_msg = format_tool_result(
                    tool_name,
                    str(result.result) if result.success else str(result.error),
                    result.success,
                )
                pending_tool_results.append(tool_result_msg)
                pending_events.append(
                    ToolCallResultEvent(
                        tool_name=tool_name,
                        tool_id=tool_id,
                        result=result,
                        injected=False,
                    )
                )

            for result_event in pending_events:
                yield result_event

            if pending_tool_results:
                self._next_message = "\n\n".join(pending_tool_results)
            else:
                self._next_message = None

            # Clear awaited tool IDs for next iteration
            self._awaited_tool_ids.clear()

        finally:
            self._is_streaming = False

    def _emit_call_end_event(
        self,
        call_number: int,
        call_start_time: float,
        ttft: float | None,
        usage_metadata: Any,
        *,
        cancelled: bool,
    ) -> list[LLMCallEndEvent]:
        """Create and track metrics for an LLM call end event."""
        duration = time.time() - call_start_time

        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0
        cached_tokens = 0
        thoughts_tokens = 0

        if usage_metadata:
            prompt_tokens = getattr(usage_metadata, "prompt_token_count", 0) or 0
            completion_tokens = getattr(usage_metadata, "candidates_token_count", 0) or 0
            total_tokens = getattr(usage_metadata, "total_token_count", 0) or 0
            cached_tokens = getattr(usage_metadata, "cached_content_token_count", 0) or 0
            thoughts_tokens = getattr(usage_metadata, "thoughts_token_count", 0) or 0

        self._total_prompt_tokens += prompt_tokens
        self._total_completion_tokens += completion_tokens
        self._total_tokens += total_tokens
        self._total_cached_tokens += cached_tokens
        self._total_thoughts_tokens += thoughts_tokens

        self._call_metrics.append(
            {
                "call_number": call_number,
                "ttft": ttft,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "cached_tokens": cached_tokens,
                "thoughts_tokens": thoughts_tokens,
                "duration": duration,
                "cancelled": cancelled,
            }
        )

        return [
            LLMCallEndEvent(
                call_number=call_number,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cached_tokens=cached_tokens,
                thoughts_tokens=thoughts_tokens,
                duration=duration,
                cancelled=cancelled,
            )
        ]

    async def _process_chunk(self, chunk: Any) -> AsyncIterator[Any]:
        """Process a single chunk through StreamBlocks."""
        events = self.processor.process_chunk(chunk)
        for event in events:
            yield event

    async def _execute_tool(self, tool_name: str, tool_id: str, parameters: dict[str, Any]) -> ToolResult:
        """Execute a tool and queue the result."""
        result = await self.executor.execute(tool_name, parameters, context=self.context)
        await self._tool_results.put((tool_name, tool_id, result))
        self._pending_tools.pop(tool_id, None)
        return result

    async def _cancel_pending_tools(self) -> None:
        """Cancel all pending tool executions."""
        for tool_id, task in list(self._pending_tools.items()):
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self._pending_tools.clear()
