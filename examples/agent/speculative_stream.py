"""Speculative Agent Stream - The key innovation for parallel tool execution.

This module implements speculative continuation:
- LLM streams continuously (never stops at tool calls)
- Tools execute in parallel via asyncio.create_task()
- When tool completes:
  - If LLM finished → inject result, start new call
  - If LLM still streaming → cancel stream, inject result, resume

This pattern is adapted from PausableGeminiStream in live_feedback examples.
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

from examples.agent.blocks import FinalAnswer, ToolCall, ToolCallContent, ToolCallMetadata
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


class SpeculativeAgentStream:
    """Stream controller with parallel tool execution.

    Key Features:
    - Tools execute in background while LLM continues streaming
    - Results are injected as soon as available
    - Speculative content may be discarded (regenerated with real results)

    Usage:
        stream = SpeculativeAgentStream(client, executor, tools)
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
    ) -> None:
        """Initialize the speculative stream.

        Args:
            client: Gemini client instance
            executor: Tool executor with registered tools
            tools: List of tool definitions (for system prompt)
            model_id: Model to use
            max_iterations: Maximum number of LLM calls
            context: Optional RunContext for dependency injection
        """
        self.client = client
        self.executor = executor
        self.tools = tools
        self.model_id = model_id
        self.max_iterations = max_iterations
        self.context = context

        # Build system prompt
        self.system_prompt = build_system_prompt(tools)

        # Chat instance (created per run)
        self._chat: Any = None

        # Next message to send to chat
        self._next_message: str | None = None

        # Tool execution state
        self._pending_tools: dict[str, asyncio.Task[ToolResult]] = {}
        self._tool_results: asyncio.Queue[tuple[str, str, ToolResult]] = asyncio.Queue()

        # Stream control
        self._is_streaming = False
        self._done = False
        self._tools_called = 0
        self._tool_call_counter = 0

        # Metrics tracking
        self._llm_call_count = 0
        self._total_prompt_tokens = 0
        self._total_completion_tokens = 0
        self._total_tokens = 0
        self._total_cached_tokens = 0
        self._total_thoughts_tokens = 0
        self._call_metrics: list[dict[str, Any]] = []

        # Setup StreamBlocks registry (processor created fresh each iteration)
        self._syntax = DelimiterFrontmatterSyntax(
            start_delimiter="!!start",
            end_delimiter="!!end",
        )
        self._registry = Registry(syntax=self._syntax)
        self._registry.register("tool_call", ToolCall)
        self._registry.register("final_answer", FinalAnswer)
        self.processor: StreamBlockProcessor[Any] | None = None

    def _create_processor(self) -> StreamBlockProcessor[Any]:
        """Create a fresh StreamBlockProcessor for each iteration."""
        return StreamBlockProcessor(self._registry, emit_text_deltas=True)

    async def run(self, task: str) -> AsyncIterator[Any]:
        """Run the agent on a task, yielding events.

        Args:
            task: The task/question to answer

        Yields:
            Various events: TextDeltaEvent, ActionEvent, ToolStartedEvent,
            ObservationEvent, StreamCancelledEvent, AnswerEvent
        """
        # Create chat with system instruction and disabled thinking
        self._chat = self.client.aio.chats.create(
            model=self.model_id,
            config=GenerateContentConfig(
                system_instruction=self.system_prompt,
                thinking_config=ThinkingConfig(thinking_budget=0),
            ),
        )

        # First message is the task
        self._next_message = f"Task: {task}"

        iteration = 0
        consecutive_no_progress = 0  # Track iterations without any blocks

        while not self._done and iteration < self.max_iterations:
            iteration += 1
            made_progress = False  # Track if we extracted any blocks this iteration

            # Stream from LLM with injection support
            async for event in self._stream_with_injection():
                yield event

                # Handle extracted blocks
                if isinstance(event, BlockExtractedEvent):
                    made_progress = True  # We got at least one block
                    block = event.block
                    block_type = block.metadata.block_type

                    if block_type == "tool_call":
                        # Tool call detected - start execution in background
                        self._tool_call_counter += 1
                        tool_name = block.metadata.tool_name  # type: ignore[attr-defined]
                        tool_id = block.metadata.id
                        parameters = block.content.parameters  # type: ignore[attr-defined]

                        yield ToolCallEvent(
                            tool_name=tool_name,
                            tool_id=tool_id,
                            parameters=parameters,
                        )

                        # Start tool in background - LLM continues!
                        task_obj = asyncio.create_task(self._execute_tool(tool_name, tool_id, parameters))
                        self._pending_tools[tool_id] = task_obj
                        self._tools_called += 1

                        yield ToolStartedEvent(tool_name=tool_name, tool_id=tool_id)

                    elif block_type == "final_answer":
                        # Done! Cancel any pending tools
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

                # Also count tool results as progress (tool results came back)
                elif isinstance(event, ToolCallResultEvent):
                    made_progress = True

            # Track consecutive iterations without progress to detect stuck loops
            if made_progress:
                consecutive_no_progress = 0
            else:
                consecutive_no_progress += 1
                # If 2 consecutive iterations have no blocks, LLM isn't following format
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

            # If no next message but still have pending tools, wait for them
            if self._next_message is None and not self._done and self._pending_tools:
                # Wait for at least one tool to complete
                if self._pending_tools:
                    # Wait for any pending tool to complete
                    _done, _ = await asyncio.wait(
                        list(self._pending_tools.values()),
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                    # Collect results
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

        # If we exited without final_answer, yield a timeout message
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
        """Stream from LLM, checking for tool results to inject.

        This is the core of speculative continuation:
        - Stream chunks from LLM via chat.send_message_stream()
        - Check for completed tools after each chunk
        - If tool completed: inject result as next message, break to restart
        """
        self._is_streaming = True

        # Create fresh processor for this iteration (important: reset state)
        self.processor = self._create_processor()

        # Get the message to send (task or tool observation)
        message_to_send = self._next_message
        if message_to_send is None:
            # No message to send - this shouldn't happen
            self._is_streaming = False
            return

        # Track metrics for this call
        self._llm_call_count += 1
        call_number = self._llm_call_count
        call_start_time = time.time()
        first_token_time: float | None = None
        ttft: float | None = None
        last_usage_metadata: Any = None
        was_cancelled = False

        # Emit call start event
        yield LLMCallStartEvent(call_number=call_number, timestamp=call_start_time)

        try:
            # Use chat interface - it manages conversation history automatically
            response = await self._chat.send_message_stream(message_to_send)

            accumulated = ""

            async for chunk in response:
                # Track first token timing
                if first_token_time is None:
                    first_token_time = time.time()
                    ttft = first_token_time - call_start_time
                    yield LLMFirstTokenEvent(call_number=call_number, ttft=ttft)

                # Extract usage metadata (Gemini provides this on chunks)
                if hasattr(chunk, "usage_metadata") and chunk.usage_metadata:
                    last_usage_metadata = chunk.usage_metadata

                # Check if any tool completed while we were streaming
                if not self._tool_results.empty():
                    # TOOL COMPLETED WHILE STREAMING!
                    tool_name, tool_id, result = await self._tool_results.get()

                    # Yield cancellation event
                    yield StreamCancelledEvent(
                        reason=f"Tool {tool_name} completed",
                        accumulated_text=accumulated,
                    )

                    was_cancelled = True

                    # Emit call end event before injecting result
                    for end_event in self._emit_call_end_event(
                        call_number, call_start_time, ttft, last_usage_metadata, cancelled=True
                    ):
                        yield end_event

                    # Set next message to be the tool result
                    tool_result_msg = format_tool_result(
                        tool_name,
                        str(result.result) if result.success else str(result.error),
                        result.success,
                    )
                    self._next_message = tool_result_msg

                    yield ToolCallResultEvent(
                        tool_name=tool_name,
                        tool_id=tool_id,
                        result=result,
                        injected=True,
                    )

                    # Break to restart with injected result
                    self._is_streaming = False
                    return

                # Process chunk through StreamBlocks
                if hasattr(chunk, "text") and chunk.text:
                    accumulated += chunk.text

                # Yield chunk for StreamBlocks processing
                async for event in self._process_chunk(chunk):
                    yield event

            # Stream finished naturally - chat history is auto-managed

            # Emit call end event for natural completion
            if not was_cancelled:
                for end_event in self._emit_call_end_event(
                    call_number, call_start_time, ttft, last_usage_metadata, cancelled=False
                ):
                    yield end_event

            # CRITICAL: Finalize processor to emit any remaining blocks
            if self.processor is not None:
                final_events = self.processor.finalize()
                for event in final_events:
                    yield event

            # Check for any pending tool results and inject them
            # Collect all pending results first
            pending_tool_results: list[str] = []
            pending_events: list[ToolCallResultEvent] = []

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

            # Yield all tool result events
            for result_event in pending_events:
                yield result_event

            # If we have pending tool results, combine them and set as next message
            if pending_tool_results:
                self._next_message = "\n\n".join(pending_tool_results)
            else:
                # No pending tools - clear next message (LLM finished naturally)
                self._next_message = None

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

        # Extract token counts from usage metadata
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

        # Update totals
        self._total_prompt_tokens += prompt_tokens
        self._total_completion_tokens += completion_tokens
        self._total_tokens += total_tokens
        self._total_cached_tokens += cached_tokens
        self._total_thoughts_tokens += thoughts_tokens

        # Store call metrics
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
        # Use the processor's synchronous chunk processing
        events = self.processor.process_chunk(chunk)
        for event in events:
            yield event

    async def _execute_tool(self, tool_name: str, tool_id: str, parameters: dict[str, Any]) -> ToolResult:
        """Execute a tool and queue the result.

        This runs in the background while the LLM continues streaming.
        """
        result = await self.executor.execute(tool_name, parameters, context=self.context)

        # Queue result for injection
        await self._tool_results.put((tool_name, tool_id, result))

        # Remove from pending
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
