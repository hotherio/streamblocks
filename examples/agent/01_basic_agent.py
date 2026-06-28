#!/usr/bin/env python3
"""
Basic Agent Example with Live Streaming Output (Speculative Continuation)

Demonstrates the StreamBlocks Agent with real-time event visualization.
Shows text streaming, block detection, tool calls, and turn-by-turn progress.

This is the SPECULATIVE approach:
- Tools execute IN PARALLEL while LLM continues streaming
- Results injected mid-stream when ready
- Stream may be cancelled and resumed when tool completes

Compare with 02_sequential_agent.py for the traditional (non-speculative) approach.

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

from rich import box

from examples.agent.agent import Agent
from examples.agent.display import AgentEventRenderer, console
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
# STREAMBLOCKS SPECULATIVE AGENT
# =============================================================================


async def run_streamblocks_speculative(task: str) -> tuple[str, int, float, int]:
    """Run the StreamBlocks speculative agent.

    Returns:
        (answer, tools_called, elapsed_time, total_tokens)
    """
    # Initialize renderer
    renderer = AgentEventRenderer()
    renderer.render_header(
        "STREAMBLOCKS SPECULATIVE AGENT",
        "(Tools execute IN PARALLEL with LLM streaming)",
    )

    # Create agent
    agent = Agent(model="gemini-2.5-flash")

    # Register complex tools using decorators
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

    # Track state for visualization
    turn = 1
    tools_called = 0
    final_answer = ""
    start_time = time.time()

    # Track metrics
    llm_call_metrics: list[dict[str, Any]] = []
    current_call_ttft: float | None = None

    # Stream events in real-time
    async for event in agent.run_stream(task):
        # Use renderer for most events
        if isinstance(event, LLMCallStartEvent):
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
        elif isinstance(event, ToolCallResultEvent):
            tools_called += 1
            renderer.render_tool_result(event)
        elif isinstance(event, StreamCancelledEvent):
            renderer.render_stream_cancelled(event)
            turn += 1
        elif isinstance(event, AnswerEvent):
            final_answer = event.answer
            tools_called = event.tools_called
        else:
            # Let renderer handle all other events
            renderer.render_event(event)

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
# PYDANTIC AI AGENT (COMPARISON)
# =============================================================================


async def run_pydantic_ai(task: str) -> tuple[str, int, float, int]:
    """Run the Pydantic AI agent with native tool calling.

    Returns:
        (answer, tools_called, elapsed_time, total_tokens)
    """
    if not PYDANTIC_AI_AVAILABLE or PydanticAgent is None or GoogleModel is None:
        console.print("[red]Pydantic AI is not available. Install with: pip install pydantic-ai[/red]")
        return "", 0, 0.0, 0

    # Initialize renderer
    renderer = AgentEventRenderer()
    console.print()
    renderer.render_header(
        "PYDANTIC AI AGENT",
        "(Native tool calling)",
    )

    # Create model and agent with thinking disabled
    model = GoogleModel("gemini-2.5-flash")
    gemini_thinking_config = {
        "include_thoughts": False,
        "thinking_budget": 0,
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

                console.print(f"\n[blue][LLM Call {llm_call_count} started][/blue]")

                async with node.stream(agent_run.ctx) as stream:
                    async for event in stream:
                        # Track TTFT
                        if first_token_time is None:
                            first_token_time = time.time()
                            ttft = first_token_time - call_start
                            console.print(f"[dim][TTFT: {ttft * 1000:.0f}ms][/dim]")

                        # Stream text deltas
                        if hasattr(event, "delta") and event.delta:
                            import sys

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
                console.print(f"\n[blue][LLM Call {llm_call_count} completed: {duration:.2f}s][/blue]")

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
                            console.print(f"[bold green][Tool result (SUCCESS): {result_str}][/]")

    elapsed = time.time() - start_time

    # Get result and usage
    result = agent_run.result
    usage = agent_run.usage()

    answer = str(result.output) if result else "No result"

    # Render results with Rich
    renderer.render_results_summary(answer, tools_called, 1, elapsed)
    renderer.render_token_metrics_summary(
        usage.requests,
        usage.input_tokens,
        usage.output_tokens,
        usage.input_tokens + usage.output_tokens,
    )

    # Simple per-call breakdown for Pydantic AI
    from rich.table import Table

    table = Table(title="Per-Call Breakdown", box=box.ROUNDED, border_style="cyan")
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
    """Run both agents and compare results."""
    from rich import box
    from rich.panel import Panel
    from rich.table import Table

    # Check for API key
    if not (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
        console.print("[red]Error: Set GEMINI_API_KEY or GOOGLE_API_KEY environment variable[/red]")
        return

    console.print()
    console.print(
        Panel(
            "[bold]StreamBlocks vs Pydantic AI[/bold]\n[dim]Speculative Agent Comparison[/dim]",
            border_style="magenta",
            box=box.DOUBLE,
        )
    )
    console.print()
    console.print("[bold]Using COMPLEX TOOLS with simulated latency:[/bold]")
    console.print("  [yellow]search_products:[/yellow] 1.2s (complex filters, nested objects)")
    console.print("  [yellow]create_order:[/yellow] 1.5s (nested address, items)")
    console.print("  [yellow]get_analytics:[/yellow] 2.0s (aggregations, time series)")
    console.print()

    # Use complex task
    task = COMPLEX_TASK

    # Run StreamBlocks speculative agent
    _sb_answer, sb_tools, sb_time, sb_tokens = await run_streamblocks_speculative(task)

    # Run Pydantic AI agent
    _pai_answer, pai_tools, pai_time, pai_tokens = await run_pydantic_ai(task)

    # Final comparison
    console.print()
    comparison_table = Table(
        title="Comparison Summary",
        box=box.DOUBLE,
        border_style="magenta",
    )
    comparison_table.add_column("Metric", style="bold")
    comparison_table.add_column("StreamBlocks", style="green", justify="right")
    comparison_table.add_column("Pydantic AI", style="blue", justify="right")

    comparison_table.add_row("Tools called", str(sb_tools), str(pai_tools))
    comparison_table.add_row("Time (seconds)", f"{sb_time:.2f}", f"{pai_time:.2f}")
    comparison_table.add_row("Total tokens", str(sb_tokens), str(pai_tokens))

    console.print(comparison_table)

    console.print()
    console.print("[bold cyan]Note:[/bold cyan] StreamBlocks uses [green]SPECULATIVE[/green] continuation:")
    console.print("[dim]  - Tools run in parallel with LLM streaming[/dim]")
    console.print("[dim]  - Results injected mid-stream when ready[/dim]")
    console.print()
    console.print("[dim]Pydantic AI uses native function calling (API-level)[/dim]")
    console.print()
    console.print("[dim]With slow tools (1.2-2.0s), speculative execution can save time[/dim]")
    console.print("[dim]by running tools while the LLM continues generating.[/dim]")
    console.print()
    console.print("[dim]See 02_sequential_agent.py for the parallel-after-LLM comparison.[/dim]")
    console.print("[dim]See 03_batched_speculative.py for the batched approach.[/dim]")


if __name__ == "__main__":
    asyncio.run(main())
