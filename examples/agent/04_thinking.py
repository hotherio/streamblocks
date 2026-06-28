#!/usr/bin/env python3
"""
Hybrid Thinking Mode Demo - Dynamic thinking control per LLM call.

Demonstrates DYNAMIC THINKING control with StreamBlocks vs constant thinking with Pydantic AI:

StreamBlocks (ThinkingAgentStream):
- First LLM call uses thinking (thinking_budget=1024) for initial reasoning
- Subsequent calls after tool feedback use NO thinking (thinking_budget=0) for faster response
- Creates NEW chat per call to enable dynamic thinking config

Pydantic AI:
- Uses thinking throughout ALL calls (thinking_budget=1024)
- Consistent reasoning mode across the entire conversation

This demonstrates the flexibility of StreamBlocks to control model behavior per-call,
which is useful for optimizing latency vs. reasoning quality tradeoffs.

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

from google import genai
from rich import box

from examples.agent.display import AgentEventRenderer, console, truncate
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
from examples.agent.executor import ToolExecutor
from examples.agent.thinking_stream import ThinkingAgentStream
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
# STREAMBLOCKS THINKING AGENT (Hybrid Thinking Mode)
# =============================================================================


async def run_streamblocks_thinking(task: str) -> tuple[str, int, float, int]:
    """Run the StreamBlocks thinking agent with dynamic thinking config.

    First LLM call uses thinking (budget=128), subsequent calls disable thinking (budget=0).

    Returns:
        (answer, tools_called, elapsed_time, total_tokens)
    """
    # Initialize renderer
    renderer = AgentEventRenderer()
    renderer.render_header(
        "STREAMBLOCKS THINKING AGENT (Hybrid Mode)",
        "(First call: thinking=1024, Subsequent calls: thinking=0)",
    )

    # Create Gemini client
    client = genai.Client()

    # Create tool executor
    executor = ToolExecutor()

    # Register tool implementations with docstrings (executor extracts schema from type hints)
    async def search_products_handler(
        query: str,
        category: Literal["electronics", "clothing", "home", "sports"],
        price_range: PriceRange,
        filters: list[Filter],
        sort_by: str = "relevance",
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search product catalog with filters.

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

        Returns:
            List of matching products
        """
        return await search_products_impl(query, category, price_range, filters, sort_by, limit)

    async def create_order_handler(
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

    async def get_analytics_handler(
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

    executor.register(search_products_handler, name="search_products")
    executor.register(create_order_handler, name="create_order")
    executor.register(get_analytics_handler, name="get_analytics")

    # Get tool definitions from executor (for system prompt building)
    tool_definitions = list(executor._tools.values())

    # Create ThinkingAgentStream with hybrid thinking mode
    # First call: thinking_budget=128, subsequent calls: thinking_budget=0
    stream = ThinkingAgentStream(
        client=client,
        executor=executor,
        tools=tool_definitions,
        model_id="gemini-2.5-flash",
        first_call_thinking_budget=1024,
        subsequent_thinking_budget=0,
    )

    renderer.render_task(task)

    # Track state for visualization
    turn = 1
    tools_called = 0
    final_answer = ""
    start_time = time.time()

    # Track metrics
    llm_call_metrics: list[dict[str, Any]] = []
    current_call_ttft: float | None = None

    # Stream events in real-time
    async for event in stream.run(task):
        if isinstance(event, TextDeltaEvent):
            renderer.render_text_delta(event)

        elif isinstance(event, BlockExtractedEvent):
            renderer.render_block_extracted(event)

        elif isinstance(event, ToolCallEvent):
            renderer.render_tool_call(event)

        elif isinstance(event, ToolStartedEvent):
            renderer.render_tool_started(event)

        elif isinstance(event, ToolCallResultEvent):
            tools_called += 1
            renderer.render_tool_result(event)

        elif isinstance(event, StreamCancelledEvent):
            renderer.render_stream_cancelled(event)
            turn += 1

        elif isinstance(event, LLMCallStartEvent):
            renderer.render_llm_start(event)
            current_call_ttft = None

        elif isinstance(event, LLMFirstTokenEvent):
            current_call_ttft = event.ttft
            renderer.render_llm_first_token(event)

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
            renderer.render_llm_end(event)

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

    # Render results with Rich
    renderer.render_results_summary(final_answer, tools_called, turn, elapsed)
    renderer.render_token_metrics_summary(
        len(llm_call_metrics),
        total_prompt_tokens,
        total_completion_tokens,
        total_tokens,
        total_cached_tokens,
        total_thoughts_tokens,
    )
    renderer.render_token_metrics_table(llm_call_metrics)

    return final_answer, tools_called, elapsed, total_tokens


# =============================================================================
# PYDANTIC AI AGENT (Constant Thinking Mode)
# =============================================================================


async def run_pydantic_ai(task: str) -> tuple[str, int, float, int]:
    """Run the Pydantic AI agent with thinking enabled throughout.

    Uses thinking_budget=1024 for ALL LLM calls (consistent reasoning mode).

    Returns:
        (answer, tools_called, elapsed_time, total_tokens)
    """
    if not PYDANTIC_AI_AVAILABLE or PydanticAgent is None or GoogleModel is None:
        console.print("[red]Pydantic AI is not available. Install with: pip install pydantic-ai[/]")
        return "", 0, 0.0, 0

    # Initialize renderer
    renderer = AgentEventRenderer()
    renderer.render_header(
        "PYDANTIC AI AGENT (Constant Thinking)",
        "(thinking_budget=1024 for ALL calls)",
    )

    # Create model and agent with thinking ENABLED throughout
    model = GoogleModel("gemini-2.5-flash")
    gemini_thinking_config = {
        "include_thoughts": False,
        "thinking_budget": 1024,  # Thinking enabled for ALL calls
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
        """Search product catalog with filters.

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
            List of matching products
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

    renderer.render_task(task)

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

                console.print(f"\n[blue][LLM Call {llm_call_count} started][/]")

                async with node.stream(agent_run.ctx) as stream:
                    async for event in stream:
                        # Track TTFT
                        if first_token_time is None:
                            first_token_time = time.time()
                            ttft = first_token_time - call_start
                            console.print(f"[dim][TTFT: {ttft * 1000:.0f}ms][/dim]")

                        # Stream text deltas
                        if hasattr(event, "delta") and event.delta:
                            sys.stdout.write(str(event.delta))
                            sys.stdout.flush()

                duration = time.time() - call_start
                llm_call_metrics.append(
                    {
                        "call": llm_call_count,
                        "ttft": ttft,
                        "duration": duration,
                    }
                )
                console.print(f"\n[blue][LLM Call {llm_call_count} completed: {duration:.2f}s][/]")

            elif PydanticAgent.is_call_tools_node(node):
                # Tool calls
                async with node.stream(agent_run.ctx) as handle_stream:
                    async for event in handle_stream:
                        if isinstance(event, FunctionToolCallEvent):
                            console.print(f"\n[bold yellow][Tool call: {event.part.tool_name}][/]")
                            args_str = str(event.part.args)
                            if len(args_str) > 200:
                                args_str = args_str[:200] + "..."
                            console.print(f"[dim]  Parameters: {args_str}[/dim]")
                        elif isinstance(event, FunctionToolResultEvent):
                            tools_called += 1
                            result_str = str(event.result.content)
                            if len(result_str) > 200:
                                result_str = result_str[:200] + "..."
                            console.print(f"\n[bold green][Tool result (SUCCESS): {result_str}][/]")

    elapsed = time.time() - start_time

    # Get result and usage
    result = agent_run.result
    usage = agent_run.usage()

    answer = str(result.output) if result else "No result"

    # Render results with Rich
    renderer.render_results_summary(answer, tools_called, llm_call_count, elapsed)
    renderer.render_token_metrics_summary(
        usage.requests,
        usage.input_tokens,
        usage.output_tokens,
        usage.input_tokens + usage.output_tokens,
    )

    # Build per-call breakdown table
    from rich.table import Table

    table = Table(
        title="Per-Call Breakdown",
        box=box.ROUNDED,
        border_style="cyan",
    )
    table.add_column("Call", style="cyan", justify="right")
    table.add_column("TTFT", style="yellow", justify="right")
    table.add_column("Duration", justify="right")

    for m in llm_call_metrics:
        ttft_str = f"{m['ttft'] * 1000:.0f}ms" if m["ttft"] is not None else "N/A"
        table.add_row(str(m["call"]), ttft_str, f"{m['duration']:.2f}s")

    console.print()
    console.print(table)

    total_tokens = usage.input_tokens + usage.output_tokens
    return answer, tools_called, elapsed, total_tokens


# =============================================================================
# MAIN
# =============================================================================


async def main() -> None:
    """Run both agents and compare thinking mode behavior."""
    from rich.panel import Panel

    # Check for API key
    if not (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
        console.print("[red]Error: Set GEMINI_API_KEY or GOOGLE_API_KEY environment variable[/]")
        return

    # Intro panel
    intro_content = (
        "[bold]StreamBlocks vs Pydantic AI - Hybrid Thinking Mode Comparison[/]\n\n"
        "[bold]THINKING MODE CONFIGURATION:[/]\n"
        "  StreamBlocks: First call thinking=1024, subsequent calls thinking=0\n"
        "  Pydantic AI:  ALL calls thinking=1024\n\n"
        "[dim]Using COMPLEX TOOLS with simulated latency:[/]\n"
        "  • search_products: 1.2s (complex filters, nested objects)\n"
        "  • create_order: 1.5s (nested address, items)\n"
        "  • get_analytics: 2.0s (aggregations, time series)"
    )
    console.print()
    console.print(Panel(intro_content, border_style="magenta", box=box.DOUBLE))
    console.print()

    # Use complex task
    task = COMPLEX_TASK

    # Run StreamBlocks thinking agent (hybrid mode)
    _sb_answer, sb_tools, sb_time, sb_tokens = await run_streamblocks_thinking(task)

    # Run Pydantic AI agent (constant thinking)
    _pai_answer, pai_tools, pai_time, pai_tokens = await run_pydantic_ai(task)

    # Final comparison using renderer
    renderer = AgentEventRenderer()
    renderer.render_comparison_table(
        "StreamBlocks",
        "Pydantic AI",
        [
            ("Thinking mode", "Hybrid (1024→0)", "Constant (1024)"),
            ("Tools called", str(sb_tools), str(pai_tools)),
            ("Time (seconds)", f"{sb_time:.2f}", f"{pai_time:.2f}"),
            ("Total tokens", str(sb_tokens), str(pai_tokens)),
        ],
    )

    renderer.render_notes(
        [
            "KEY DIFFERENCES:",
            "",
            "  StreamBlocks (Hybrid Thinking):",
            "    - First call uses thinking (better initial reasoning)",
            "    - Subsequent calls disable thinking (faster after feedback)",
            "    - thoughts_tokens > 0 on first call, = 0 on subsequent calls",
            "",
            "  Pydantic AI (Constant Thinking):",
            "    - ALL calls use thinking mode",
            "    - Consistent reasoning quality throughout",
            "    - Cannot dynamically control thinking per-call",
            "",
            "This demonstrates StreamBlocks' flexibility for per-call model configuration.",
        ]
    )


if __name__ == "__main__":
    asyncio.run(main())
