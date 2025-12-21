#!/usr/bin/env python3
"""Batched Speculative Agent Example - Wait for ALL Tools Before Next LLM Call.

Demonstrates the batched approach where:
- LLM streams and tool calls are detected
- Tools execute in background (parallel with streaming)
- Wait for LLM to finish AND all tools to complete
- Inject ALL results together before next LLM call

This is the BATCHED approach:
- LLM streams naturally (no interruption)
- Tools run in parallel while streaming
- After LLM finishes, wait for ALL tools
- All results injected at once
- Fewer LLM API calls than speculative

Compare with:
- 01_basic_agent.py: SPECULATIVE - cancels stream when first tool completes
- 02_sequential_agent.py: PARALLEL-AFTER-LLM - tools only start after LLM finishes

Uses COMPLEX TOOLS to demonstrate StreamBlocks' advantages:
- Complex schemas (nested objects, enums, arrays)
- Slow execution (1.2-2.0s simulated latency)
- Multi-step e-commerce task

Requires: GEMINI_API_KEY or GOOGLE_API_KEY environment variable.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from typing import Any, Literal

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from google import genai  # type: ignore[import-not-found]

from examples.agent.batched_stream import BatchedAgentStream
from examples.agent.events import (
    AnswerEvent,
    LLMCallEndEvent,
    LLMCallStartEvent,
    LLMFirstTokenEvent,
    ToolCallEvent,
    ToolCallResultEvent,
    ToolStartedEvent,
)
from examples.agent.executor import ToolExecutor
from examples.agent.tools import (
    COMPLEX_TASK,
    DateRange,
    Filter,
    OrderItem,
    PriceRange,
    ShippingAddress,
    create_order_impl,
    get_analytics_impl,
    search_products_impl,
)
from hother.streamblocks import BlockExtractedEvent, TextDeltaEvent

# Check for Pydantic AI
try:
    from pydantic_ai import Agent as PydanticAgent
    from pydantic_ai.messages import FunctionToolCallEvent, FunctionToolResultEvent
    from pydantic_ai.models.google import GoogleModel

    PYDANTIC_AI_AVAILABLE = True
except ImportError:
    PYDANTIC_AI_AVAILABLE = False
    PydanticAgent = None
    GoogleModel = None
    FunctionToolCallEvent = None
    FunctionToolResultEvent = None


# =============================================================================
# STREAMBLOCKS BATCHED AGENT
# =============================================================================


async def run_streamblocks_batched(task: str) -> tuple[str, int, float, int]:
    """Run the StreamBlocks batched agent.

    Returns:
        (answer, tools_called, elapsed_time, llm_calls)
    """
    print("=" * 70)
    print("STREAMBLOCKS BATCHED AGENT")
    print("(Tools run in background, ALL results batched before next LLM call)")
    print("=" * 70)
    print()

    # Initialize client
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    client = genai.Client(api_key=api_key)

    # Create executor and register complex tools
    executor = ToolExecutor()

    @executor.register(
        name="search_products",
        description="""Search product catalog with filters.

Args:
    query: Search query (e.g., "laptop", "programming laptop")
    category: One of: electronics, clothing, home, sports
    price_range: Object with "min" (default 0) and "max" price
    filters: List of filter objects. Each filter MUST use:
        - field: "specs.ram_gb" | "specs.storage_gb" | "rating"
        - operator: ">=" | "<=" | "==" | "!="
        - value: integer (16, 32, 64 for RAM; 256, 512, 1024 for storage)
    sort_by: relevance, price_asc, price_desc, rating
    limit: Max results (default 10)

Example filters:
    filters:
      - field: specs.ram_gb
        operator: ">="
        value: 16

Returns:
    List of matching products""",
    )
    async def search_products(
        query: str,
        category: Literal["electronics", "clothing", "home", "sports"],
        price_range: PriceRange,
        filters: list[Filter],
        sort_by: str = "relevance",
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        return await search_products_impl(query, category, price_range, filters, sort_by, limit)

    @executor.register(
        name="create_order",
        description="""Create a new order with nested objects.

Args:
    customer_id: The customer's unique identifier
    items: List of order items with product_id, quantity, options
    shipping_address: Address with street, city, state, zip, country
    payment_method: Payment type - credit_card, paypal, or bank_transfer
    coupon_code: Optional discount coupon code

Returns:
    Order confirmation with order_id, total, estimated_delivery, status""",
    )
    async def create_order(
        customer_id: str,
        items: list[OrderItem],
        shipping_address: ShippingAddress,
        payment_method: Literal["credit_card", "paypal", "bank_transfer"],
        coupon_code: str | None = None,
    ) -> dict[str, Any]:
        return await create_order_impl(customer_id, items, shipping_address, payment_method, coupon_code)

    @executor.register(
        name="get_analytics",
        description="""Get analytics data with aggregations.

Args:
    metric_type: Type of metric - sales, traffic, or conversion
    date_range: Date range with "start" and "end" keys (YYYY-MM-DD)
    granularity: Time granularity - hour, day, week, or month
    dimensions: Dimensions to group by - product, category, region, channel

Returns:
    Analytics data with time series, breakdowns, and summary stats""",
    )
    async def get_analytics(
        metric_type: Literal["sales", "traffic", "conversion"],
        date_range: DateRange,
        granularity: Literal["hour", "day", "week", "month"],
        dimensions: list[str],
    ) -> dict[str, Any]:
        return await get_analytics_impl(metric_type, date_range, granularity, dimensions)

    # Get tool definitions
    tools = [executor.get(name) for name in executor.list_tools() if executor.get(name) is not None]

    # Create batched stream
    stream = BatchedAgentStream(
        client=client,
        executor=executor,
        tools=tools,  # type: ignore[arg-type]
        model_id="gemini-2.5-pro",
        max_iterations=10,
    )

    print(f"Task: {task}")
    print()
    print("--- Streaming Output ---")
    print()

    # Track state
    tools_called = 0
    final_answer = ""
    tools_in_batch = 0
    start_time = time.time()

    # Track metrics
    llm_call_metrics: list[dict[str, Any]] = []
    current_call_ttft: float | None = None

    # Stream events
    async for event in stream.run(task):
        if isinstance(event, TextDeltaEvent):
            print(event.delta, end="", flush=True)

        elif isinstance(event, BlockExtractedEvent):
            block = event.block
            print(f"\n[Block: {block.metadata.block_type} id={block.metadata.id}]")

        elif isinstance(event, ToolCallEvent):
            print(f"\n[Tool call detected: {event.tool_name}]")
            params_str = str(event.parameters)
            if len(params_str) > 100:
                params_str = params_str[:100] + "..."
            print(f"  Parameters: {params_str}")

        elif isinstance(event, LLMCallStartEvent):
            print(f"\n[LLM Call {event.call_number} started]")
            current_call_ttft = None

        elif isinstance(event, LLMFirstTokenEvent):
            current_call_ttft = event.ttft
            print(f"[TTFT: {event.ttft * 1000:.0f}ms]")

        elif isinstance(event, LLMCallEndEvent):
            llm_call_metrics.append(
                {
                    "call": event.call_number,
                    "ttft": current_call_ttft,
                    "prompt_tokens": event.prompt_tokens,
                    "completion_tokens": event.completion_tokens,
                    "total_tokens": event.total_tokens,
                    "cached_tokens": event.cached_tokens,
                    "thoughts_tokens": event.thoughts_tokens,
                    "duration": event.duration,
                    "cancelled": event.cancelled,
                }
            )
            status = "cancelled" if event.cancelled else "completed"
            print(f"[LLM Call {event.call_number} {status}: {event.total_tokens} tokens, {event.duration:.2f}s]")

        elif isinstance(event, ToolStartedEvent):
            tools_in_batch += 1
            print(f"[Tool {event.tool_name} started in background ({tools_in_batch} running)]")

        elif isinstance(event, ToolCallResultEvent):
            tools_called += 1
            tools_in_batch -= 1
            status = "SUCCESS" if event.result.success else "ERROR"
            result_str = str(event.result.result)
            if len(result_str) > 200:
                result_str = result_str[:200] + "..."
            print(f"\n[Tool result ({status}): {result_str}]")

            # If this is the last tool in batch, new LLM call is coming
            if tools_in_batch == 0:
                print("\n[All tools complete - next LLM call]")

        elif isinstance(event, AnswerEvent):
            final_answer = event.answer
            tools_called = event.tools_called

    elapsed = time.time() - start_time

    # Calculate totals from collected metrics
    total_prompt_tokens = sum(m["prompt_tokens"] for m in llm_call_metrics)
    total_completion_tokens = sum(m["completion_tokens"] for m in llm_call_metrics)
    total_tokens = sum(m["total_tokens"] for m in llm_call_metrics)
    total_cached_tokens = sum(m["cached_tokens"] for m in llm_call_metrics)
    total_thoughts_tokens = sum(m["thoughts_tokens"] for m in llm_call_metrics)
    llm_calls = len(llm_call_metrics)

    print()
    print()
    print("-" * 50)
    print("RESULTS")
    print("-" * 50)
    print(f"Final Answer: {final_answer}")
    print(f"Tools called: {tools_called}")
    print(f"LLM API calls: {llm_calls}")
    print(f"Time: {elapsed:.2f}s")

    # Token metrics
    print()
    print("-" * 50)
    print("TOKEN METRICS")
    print("-" * 50)
    print(f"LLM API calls: {llm_calls}")
    print(f"Total prompt tokens: {total_prompt_tokens}")
    print(f"Total completion tokens: {total_completion_tokens}")
    print(f"Total cached tokens: {total_cached_tokens}")
    print(f"Total thoughts tokens: {total_thoughts_tokens}")
    print(f"Total tokens: {total_tokens}")
    print()
    print("Per-call breakdown:")
    print(
        f"  {'Call':<6} {'TTFT':<8} {'Prompt':<8} {'Cached':<8} {'Compl':<8} {'Thoughts':<10} {'Total':<8} {'Duration':<10} {'Status':<10}"
    )
    print("  " + "-" * 86)
    for m in llm_call_metrics:
        ttft_str = f"{m['ttft'] * 1000:.0f}ms" if m["ttft"] is not None else "N/A"
        status = "cancelled" if m["cancelled"] else "completed"
        print(
            f"  {m['call']:<6} {ttft_str:<8} {m['prompt_tokens']:<8} {m['cached_tokens']:<8} {m['completion_tokens']:<8} {m['thoughts_tokens']:<10} {m['total_tokens']:<8} {m['duration']:.2f}s     {status:<10}"
        )

    return final_answer, tools_called, elapsed, llm_calls


# =============================================================================
# PYDANTIC AI AGENT (COMPARISON)
# =============================================================================


async def run_pydantic_ai(task: str) -> tuple[str, int, float, int]:
    """Run the Pydantic AI agent with native tool calling.

    Returns:
        (answer, tools_called, elapsed_time, llm_calls)
    """
    if not PYDANTIC_AI_AVAILABLE or PydanticAgent is None or GoogleModel is None:
        print("Pydantic AI is not available. Install with: pip install pydantic-ai")
        return "", 0, 0.0, 0

    print()
    print("=" * 70)
    print("PYDANTIC AI AGENT")
    print("(Native tool calling)")
    print("=" * 70)
    print()

    # Create model and agent with thinking disabled
    model = GoogleModel("gemini-2.5-pro")
    gemini_thinking_config = {
        "include_thoughts": False,
        "thinking_budget": 128,
    }
    agent = PydanticAgent(
        model=model,
        system_prompt="You are a helpful e-commerce assistant. Use the provided tools to help customers.",
        model_settings={"gemini_thinking_config": gemini_thinking_config},
    )

    # Register the same complex tools
    @agent.tool_plain
    async def search_products(
        query: str,
        category: Literal["electronics", "clothing", "home", "sports"],
        price_range: PriceRange,
        filters: list[Filter],
        sort_by: str = "relevance",
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search product catalog with complex filters.

        Args:
            query: Search query string (e.g., "laptop", "programming laptop")
            category: Product category to search in
            price_range: Price range filter with "min" and "max" keys
            filters: List of filter objects, each with "field", "operator", "value"
            sort_by: Sort order - "relevance", "price_asc", "price_desc", "rating"
            limit: Maximum number of results to return

        Returns:
            List of matching products with id, name, price, specs, rating
        """
        return await search_products_impl(query, category, price_range, filters, sort_by, limit)

    @agent.tool_plain
    async def create_order(
        customer_id: str,
        items: list[OrderItem],
        shipping_address: ShippingAddress,
        payment_method: Literal["credit_card", "paypal", "bank_transfer"],
        coupon_code: str | None = None,
    ) -> dict[str, Any]:
        """Create a new order with nested objects.

        Args:
            customer_id: The customer's unique identifier
            items: List of order items with product_id, quantity, options
            shipping_address: Address with street, city, state, zip, country
            payment_method: Payment type - credit_card, paypal, or bank_transfer
            coupon_code: Optional discount coupon code

        Returns:
            Order confirmation with order_id, total, estimated_delivery, status
        """
        return await create_order_impl(customer_id, items, shipping_address, payment_method, coupon_code)

    @agent.tool_plain
    async def get_analytics(
        metric_type: Literal["sales", "traffic", "conversion"],
        date_range: DateRange,
        granularity: Literal["hour", "day", "week", "month"],
        dimensions: list[str],
    ) -> dict[str, Any]:
        """Get analytics data with aggregations.

        Args:
            metric_type: Type of metric - sales, traffic, or conversion
            date_range: Date range with "start" and "end" keys (YYYY-MM-DD)
            granularity: Time granularity - hour, day, week, or month
            dimensions: Dimensions to group by - product, category, region, channel

        Returns:
            Analytics data with time series, breakdowns, and summary stats
        """
        return await get_analytics_impl(metric_type, date_range, granularity, dimensions)

    print(f"Task: {task}")
    print()
    print("--- Streaming Output ---")
    print()

    # Track metrics
    llm_call_count = 0
    tools_called = 0
    start_time = time.time()
    llm_call_metrics: list[dict[str, Any]] = []

    # Use agent.iter() for detailed logging
    async with agent.iter(task) as agent_run:
        async for node in agent_run:
            if PydanticAgent.is_model_request_node(node):
                # LLM call starting
                llm_call_count += 1
                call_start = time.time()
                first_token_time: float | None = None
                ttft: float | None = None

                print(f"\n[LLM Call {llm_call_count} started]")

                async with node.stream(agent_run.ctx) as stream:
                    async for event in stream:
                        # Track TTFT
                        if first_token_time is None:
                            first_token_time = time.time()
                            ttft = first_token_time - call_start
                            print(f"[TTFT: {ttft * 1000:.0f}ms]")

                        # Stream text deltas
                        if hasattr(event, "delta") and event.delta:
                            print(event.delta, end="", flush=True)

                duration = time.time() - call_start
                llm_call_metrics.append(
                    {
                        "call": llm_call_count,
                        "ttft": ttft,
                        "duration": duration,
                    }
                )
                print(f"\n[LLM Call {llm_call_count} completed: {duration:.2f}s]")

            elif PydanticAgent.is_call_tools_node(node):
                # Tool calls
                async with node.stream(agent_run.ctx) as handle_stream:
                    async for event in handle_stream:
                        if isinstance(event, FunctionToolCallEvent):
                            print(f"\n[Tool call: {event.part.tool_name}]")
                            args_str = str(event.part.args)
                            if len(args_str) > 200:
                                args_str = args_str[:200] + "..."
                            print(f"  Parameters: {args_str}")
                        elif isinstance(event, FunctionToolResultEvent):
                            tools_called += 1
                            result_str = str(event.result.content)
                            if len(result_str) > 200:
                                result_str = result_str[:200] + "..."
                            print(f"[Tool result (SUCCESS): {result_str}]")

    elapsed = time.time() - start_time

    # Get result and usage
    result = agent_run.result
    usage = agent_run.usage()
    llm_calls = usage.requests

    answer = str(result.output) if result else "No result"
    print()
    print()
    print("-" * 50)
    print("RESULTS")
    print("-" * 50)
    print(f"Final Answer: {answer}")
    print(f"Tools called: {tools_called}")
    print(f"LLM API calls: {llm_calls}")
    print(f"Time: {elapsed:.2f}s")

    # Token metrics
    print()
    print("-" * 50)
    print("TOKEN METRICS")
    print("-" * 50)
    print(f"LLM API calls: {usage.requests}")
    print(f"Input tokens: {usage.input_tokens}")
    print(f"Output tokens: {usage.output_tokens}")
    print(f"Total tokens: {usage.input_tokens + usage.output_tokens}")
    print()
    print("Per-call breakdown:")
    print(f"  {'Call':<6} {'TTFT':<10} {'Duration':<10}")
    print("  " + "-" * 26)
    for m in llm_call_metrics:
        ttft_str = f"{m['ttft'] * 1000:.0f}ms" if m["ttft"] is not None else "N/A"
        print(f"  {m['call']:<6} {ttft_str:<10} {m['duration']:.2f}s")

    return answer, tools_called, elapsed, llm_calls


# =============================================================================
# MAIN
# =============================================================================


async def main() -> None:
    """Run both agents and compare results."""
    # Check for API key
    if not (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
        print("Error: Set GEMINI_API_KEY or GOOGLE_API_KEY environment variable")
        return

    print()
    print("StreamBlocks BATCHED vs Pydantic AI - Agent Comparison")
    print("=" * 70)
    print()
    print("Using COMPLEX TOOLS with simulated latency:")
    print("  - search_products: 1.2s (complex filters, nested objects)")
    print("  - create_order: 1.5s (nested address, items)")
    print("  - get_analytics: 2.0s (aggregations, time series)")
    print()
    print("BATCHED approach:")
    print("  - Tools run in background while LLM streams")
    print("  - Wait for ALL tools to complete")
    print("  - Inject all results together")
    print("  - Fewer LLM API calls")
    print()

    # Use complex task
    task = COMPLEX_TASK

    # Run StreamBlocks batched agent
    _sb_answer, sb_tools, sb_time, sb_llm_calls = await run_streamblocks_batched(task)

    # Run Pydantic AI agent
    _pai_answer, pai_tools, pai_time, pai_llm_calls = await run_pydantic_ai(task)

    # Final comparison
    print()
    print("=" * 70)
    print("COMPARISON SUMMARY")
    print("=" * 70)
    print()
    print(f"{'Metric':<25} {'StreamBlocks Batched':<22} {'Pydantic AI':<20}")
    print("-" * 67)
    print(f"{'Tools called':<25} {sb_tools:<22} {pai_tools:<20}")
    print(f"{'LLM API calls':<25} {sb_llm_calls:<22} {f'~{pai_llm_calls}':<20}")
    print(f"{'Time (seconds)':<25} {sb_time:<22.2f} {pai_time:<20.2f}")
    print()
    print("Key Insights:")
    print("  - BATCHED: Tools run in parallel while LLM streams")
    print("  - BATCHED: Fewer LLM calls than speculative (waits for all tools)")
    print("  - With slow tools (1.2-2.0s), parallel execution saves time")
    print()
    print("Compare with:")
    print("  - 01_basic_agent.py: SPECULATIVE (more LLM calls, faster injection)")
    print("  - 02_sequential_agent.py: PARALLEL-AFTER-LLM (tools start after LLM)")


if __name__ == "__main__":
    asyncio.run(main())
