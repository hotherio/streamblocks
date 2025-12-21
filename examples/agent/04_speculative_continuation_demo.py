#!/usr/bin/env python3
"""
Speculative Continuation Demo - KEY DEMO

Demonstrates StreamBlocks' unique advantage: LLM streams continuously while
tools execute in parallel. This shows significant time savings compared to
traditional serial tool execution.

Key Innovation:
- LLM never stops at tool calls - it continues streaming
- Tools execute in background via asyncio.create_task()
- Results are injected as soon as available
- If LLM still streaming → cancel, inject, resume
- If LLM finished → inject result, start new call

Requires: GEMINI_API_KEY or GOOGLE_API_KEY environment variable.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from dataclasses import dataclass, field

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from examples.agent.agent import Agent
from examples.agent.events import (
    AnswerEvent,
    StreamCancelledEvent,
    ToolCallEvent,
    ToolCallResultEvent,
    ToolStartedEvent,
)
from hother.streamblocks import TextDeltaEvent


@dataclass
class TimelineEvent:
    """A single event in the execution timeline."""

    timestamp: float
    event_type: str
    description: str


@dataclass
class ExecutionStats:
    """Statistics from execution."""

    total_time: float = 0.0
    tool_times: dict[str, float] = field(default_factory=dict)
    tool_overlaps: list[tuple[str, str]] = field(default_factory=list)
    stream_cancellations: int = 0
    timeline: list[TimelineEvent] = field(default_factory=list)


def format_duration(seconds: float) -> str:
    """Format duration as human-readable string."""
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    return f"{seconds:.2f}s"


async def run_speculative_demo() -> ExecutionStats:
    """Run the demo with speculative continuation."""
    print("\n" + "=" * 60)
    print("  StreamBlocks SPECULATIVE CONTINUATION Demo")
    print("=" * 60)
    print()
    print("LLM streams continuously while tools execute in parallel!")
    print()

    # Check for API key
    if not (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
        print("Error: Set GEMINI_API_KEY or GOOGLE_API_KEY environment variable")
        return ExecutionStats()

    # Create agent
    agent = Agent(model="gemini-2.5-flash")

    # Track execution stats
    stats = ExecutionStats()
    start_time = time.time()
    tool_start_times: dict[str, float] = {}

    # Register tools with varying execution times
    @agent.tool_plain
    async def slow_calculation(expression: str) -> float:
        """Perform a slow mathematical calculation (simulates complex math).

        Args:
            expression: A math expression like "2 + 2" or "sqrt(16)"

        Returns:
            The result of the calculation
        """
        import math

        # Simulate slow computation
        await asyncio.sleep(1.0)

        allowed_names = {k: v for k, v in math.__dict__.items() if not k.startswith("_")}
        allowed_names["abs"] = abs
        allowed_names["round"] = round
        return float(eval(expression, {"__builtins__": {}}, allowed_names))

    @agent.tool_plain
    async def database_lookup(query: str) -> dict[str, str | int]:
        """Look up data in a database (simulates I/O operation).

        Args:
            query: The search query

        Returns:
            Database results
        """
        # Simulate database I/O
        await asyncio.sleep(0.8)

        return {
            "query": query,
            "results": 42,
            "status": "found",
            "source": "primary_db",
        }

    @agent.tool_plain
    async def api_fetch(endpoint: str) -> dict[str, str | list[str]]:
        """Fetch data from an external API (simulates network latency).

        Args:
            endpoint: The API endpoint to call

        Returns:
            API response data
        """
        # Simulate network latency
        await asyncio.sleep(1.2)

        return {
            "endpoint": endpoint,
            "data": ["result1", "result2", "result3"],
            "cached": "false",
        }

    def log_event(event_type: str, description: str) -> None:
        """Log a timeline event."""
        elapsed = time.time() - start_time
        stats.timeline.append(TimelineEvent(elapsed, event_type, description))
        print(f"  [{elapsed:5.2f}s] {event_type:12} | {description}")

    print("--- Live Timeline ---")
    print()
    log_event("START", "Beginning task execution")

    # Task that requires multiple tool calls
    task = """I need you to:
1. Calculate the square root of 256
2. Look up "user_preferences" in the database
3. Fetch data from the "/api/v2/stats" endpoint

Give me a summary of all results."""

    print()
    print(f"Task: {task[:60]}...")
    print()

    # Run with streaming to capture events
    async for event in agent.run_stream(task):
        if isinstance(event, TextDeltaEvent):
            # LLM is streaming text (thinking/reasoning)
            pass  # Don't print every delta, too noisy

        elif isinstance(event, ToolCallEvent):
            log_event("TOOL_CALL", f"Tool call: {event.tool_name}({list(event.parameters.keys())})")

        elif isinstance(event, ToolStartedEvent):
            tool_start_times[event.tool_id] = time.time()
            log_event("TOOL_START", f"{event.tool_name} executing in background...")

        elif isinstance(event, StreamCancelledEvent):
            stats.stream_cancellations += 1
            log_event("CANCELLED", f"LLM stream cancelled - {event.reason}")

        elif isinstance(event, ToolCallResultEvent):
            if event.tool_id in tool_start_times:
                tool_time = time.time() - tool_start_times[event.tool_id]
                stats.tool_times[event.tool_name] = tool_time
                injected_str = " (INJECTED!)" if event.injected else ""
                log_event("RESULT", f"{event.tool_name} completed in {format_duration(tool_time)}{injected_str}")

        elif isinstance(event, AnswerEvent):
            stats.total_time = time.time() - start_time
            log_event("DONE", f"Final answer ready ({event.tools_called} tools used)")
            print()
            print("--- Final Answer ---")
            print(event.answer[:200] + "..." if len(event.answer) > 200 else event.answer)

    return stats


def calculate_serial_time(stats: ExecutionStats) -> float:
    """Calculate how long serial execution would have taken."""
    # In serial execution:
    # - LLM generates first tool call (~0.5s)
    # - Wait for tool execution
    # - LLM generates next tool call (~0.5s)
    # - Wait for tool execution
    # - etc.
    # Estimate 0.5s LLM time between each tool

    llm_overhead = 0.5 * (len(stats.tool_times) + 1)  # Before each tool + final answer
    tool_total = sum(stats.tool_times.values())

    return llm_overhead + tool_total


def print_comparison(stats: ExecutionStats) -> None:
    """Print comparison between speculative and serial execution."""
    print()
    print("=" * 60)
    print("  PERFORMANCE COMPARISON")
    print("=" * 60)
    print()

    serial_time = calculate_serial_time(stats)
    time_saved = serial_time - stats.total_time
    speedup = serial_time / stats.total_time if stats.total_time > 0 else 0

    print("Tool Execution Times:")
    for tool_name, tool_time in stats.tool_times.items():
        print(f"  • {tool_name}: {format_duration(tool_time)}")

    print()
    print("Execution Modes:")
    print(f"  • StreamBlocks (speculative): {format_duration(stats.total_time)}")
    print(f"  • Traditional (serial):       {format_duration(serial_time)} (estimated)")

    print()
    print("Savings:")
    print(f"  • Time saved: {format_duration(time_saved)}")
    print(f"  • Speedup: {speedup:.1f}x faster")
    print(f"  • Stream cancellations: {stats.stream_cancellations}")

    print()
    print("Why StreamBlocks is faster:")
    print("  ┌─────────────────────────────────────────────────────────┐")
    print("  │ Traditional: LLM → wait → Tool → wait → LLM → wait... │")
    print("  │ StreamBlocks: LLM streams WHILE tools run in parallel  │")
    print("  └─────────────────────────────────────────────────────────┘")


def print_timeline_diagram(stats: ExecutionStats) -> None:
    """Print a visual timeline diagram."""
    print()
    print("=" * 60)
    print("  TIMELINE VISUALIZATION")
    print("=" * 60)
    print()

    if not stats.timeline:
        print("  (No timeline data)")
        return

    # Find max time for scaling
    max_time = max(e.timestamp for e in stats.timeline)
    width = 50

    for event in stats.timeline:
        # Calculate position in timeline
        pos = int((event.timestamp / max_time) * width) if max_time > 0 else 0

        # Create timeline bar
        bar = "─" * pos + "●" + "─" * (width - pos - 1)

        # Color-code by event type
        symbol = {
            "START": "🟢",
            "ACTION": "⚡",
            "TOOL_START": "🔧",
            "CANCELLED": "⚠️",
            "RESULT": "✅",
            "DONE": "🏁",
        }.get(event.event_type, "•")

        print(f"  {symbol} {bar} [{event.timestamp:.2f}s] {event.event_type}")


async def main() -> None:
    """Run the speculative continuation demo."""
    try:
        stats = await run_speculative_demo()

        if stats.total_time > 0:
            print_comparison(stats)
            print_timeline_diagram(stats)

            print()
            print("=" * 60)
            print("  KEY TAKEAWAY")
            print("=" * 60)
            print()
            print("  StreamBlocks enables SPECULATIVE CONTINUATION:")
            print("  • LLM never blocks waiting for tools")
            print("  • Tools run in parallel with LLM streaming")
            print("  • Results injected seamlessly when ready")
            print("  • Significantly faster end-to-end execution")
            print()

    except Exception as e:
        print(f"\nError: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
