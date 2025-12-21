"""Sequential Agent Stream - Tools execute in parallel AFTER LLM finishes.

This module implements a hybrid ReAct pattern:
- LLM generates complete response
- ALL tools execute IN PARALLEL after LLM finishes
- Results injected before next LLM call

This is the baseline for comparing against SpeculativeAgentStream.

Comparison of patterns:
- Speculative (01_basic_agent.py): Tools run IN PARALLEL with LLM streaming
- Parallel-after-LLM (this file): Tools run IN PARALLEL after LLM finishes
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

from examples.agent.blocks import FinalAnswer, ToolCall
from examples.agent.events import (
    AnswerEvent,
    LLMCallEndEvent,
    LLMCallStartEvent,
    LLMFirstTokenEvent,
    ToolCallEvent,
    ToolCallResultEvent,
)
from examples.agent.prompts import build_system_prompt, format_tool_result
from hother.streamblocks import (
    BlockExtractedEvent,
    DelimiterFrontmatterSyntax,
    Registry,
    StreamBlockProcessor,
    TextDeltaEvent,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from examples.agent.context import RunContext
    from examples.agent.executor import ToolDefinition, ToolExecutor


class SequentialAgentStream:
    """Stream controller with parallel tool execution AFTER LLM finishes.

    Key Difference from SpeculativeAgentStream:
    - Tools execute ONLY after LLM finishes its response
    - Multiple tools execute IN PARALLEL using asyncio.gather()
    - Results injected all at once before next LLM turn
    - No stream cancellation or mid-stream injection

    Pattern:
    ```
    LLM: [====generate====] STOP → [all tools in parallel] → inject results → next turn
    ```

    Usage:
        stream = SequentialAgentStream(client, executor, tools)
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
        """Initialize the sequential stream.

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

        # State tracking
        self._done = False
        self._tools_called = 0

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

    def _create_processor(self) -> StreamBlockProcessor[Any]:
        """Create a fresh StreamBlockProcessor for each iteration."""
        return StreamBlockProcessor(self._registry, emit_text_deltas=True)

    async def run(self, task: str) -> AsyncIterator[Any]:
        """Run the agent on a task, yielding events.

        Args:
            task: The task/question to answer

        Yields:
            Various events: TextDeltaEvent, ActionEvent,
            ObservationEvent, AnswerEvent, LLMCallStartEvent, etc.
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
        consecutive_no_progress = 0

        while not self._done and iteration < self.max_iterations:
            iteration += 1
            made_progress = False

            # Collect all actions from this turn
            pending_actions: list[tuple[str, str, dict[str, Any]]] = []

            # Stream and collect the full response
            processor = self._create_processor()
            accumulated = ""

            # Track metrics for this call
            self._llm_call_count += 1
            call_number = self._llm_call_count
            call_start_time = time.time()
            first_token_time: float | None = None
            ttft: float | None = None
            last_usage_metadata: Any = None

            # Emit call start event
            yield LLMCallStartEvent(call_number=call_number, timestamp=call_start_time)

            # Use chat interface
            response = await self._chat.send_message_stream(self._next_message)

            # Process stream - yield text deltas but DON'T execute tools yet
            async for chunk in response:
                # Track first token timing
                if first_token_time is None:
                    first_token_time = time.time()
                    ttft = first_token_time - call_start_time
                    yield LLMFirstTokenEvent(call_number=call_number, ttft=ttft)

                # Extract usage metadata
                if hasattr(chunk, "usage_metadata") and chunk.usage_metadata:
                    last_usage_metadata = chunk.usage_metadata

                if hasattr(chunk, "text") and chunk.text:
                    accumulated += chunk.text

                # Process through StreamBlocks
                events = processor.process_chunk(chunk)
                for event in events:
                    yield event

                    if isinstance(event, BlockExtractedEvent):
                        made_progress = True
                        block = event.block
                        block_type = block.metadata.block_type

                        if block_type == "tool_call":
                            # Queue tool call for later execution (after LLM finishes)
                            tool_name = block.metadata.tool_name  # type: ignore[attr-defined]
                            tool_id = block.metadata.id
                            parameters = block.content.parameters  # type: ignore[attr-defined]

                            yield ToolCallEvent(
                                tool_name=tool_name,
                                tool_id=tool_id,
                                parameters=parameters,
                            )

                            pending_actions.append((tool_name, tool_id, parameters))

                        elif block_type == "final_answer":
                            # Done!
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

            # Finalize processor to emit any remaining blocks
            final_events = processor.finalize()
            for event in final_events:
                yield event

                if isinstance(event, BlockExtractedEvent):
                    made_progress = True
                    block = event.block
                    block_type = block.metadata.block_type

                    if block_type == "tool_call":
                        tool_name = block.metadata.tool_name  # type: ignore[attr-defined]
                        tool_id = block.metadata.id
                        parameters = block.content.parameters  # type: ignore[attr-defined]

                        yield ToolCallEvent(
                            tool_name=tool_name,
                            tool_id=tool_id,
                            parameters=parameters,
                        )

                        pending_actions.append((tool_name, tool_id, parameters))

                    elif block_type == "final_answer":
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

            # Emit call end event
            for end_event in self._emit_call_end_event(
                call_number, call_start_time, ttft, last_usage_metadata, cancelled=False
            ):
                yield end_event

            # NOW execute ALL tools IN PARALLEL (after LLM finished)
            if not self._done and pending_actions:
                # Execute all tools in parallel using asyncio.gather
                tasks = [
                    self.executor.execute(tool_name, parameters, context=self.context)
                    for tool_name, tool_id, parameters in pending_actions
                ]
                results = await asyncio.gather(*tasks)

                # Collect all tool results to send as next message
                tool_results_msgs: list[str] = []

                # Inject all results
                for (tool_name, tool_id, parameters), result in zip(pending_actions, results, strict=True):
                    self._tools_called += 1
                    made_progress = True

                    # Format tool result
                    tool_result_msg = format_tool_result(
                        tool_name,
                        str(result.result) if result.success else str(result.error),
                        result.success,
                    )
                    tool_results_msgs.append(tool_result_msg)

                    yield ToolCallResultEvent(
                        tool_name=tool_name,
                        tool_id=tool_id,
                        result=result,
                        injected=False,  # Not mid-stream injection
                    )

                # Set next message to combined tool results
                self._next_message = "\n\n".join(tool_results_msgs)

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
