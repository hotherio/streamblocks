"""Rich display module for agent examples.

Provides beautiful terminal output using Rich library.
Shared across all agent examples (01-04) for consistent styling.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

if TYPE_CHECKING:
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
    from hother.streamblocks import BlockExtractedEvent, TextDeltaEvent

# Module-level console (singleton)
console = Console()


@dataclass
class DisplayConfig:
    """Configuration for agent display rendering."""

    truncate_params_at: int = 100
    truncate_result_at: int = 200
    tool_style: str = "yellow"
    llm_style: str = "blue"
    success_style: str = "green"
    error_style: str = "red"
    cancelled_style: str = "yellow"
    header_border_style: str = "cyan"
    metrics_border_style: str = "cyan"
    comparison_border_style: str = "magenta"


def truncate(text: str, max_length: int) -> str:
    """Truncate text with ellipsis if too long."""
    text_str = str(text)
    if len(text_str) > max_length:
        return text_str[:max_length] + "..."
    return text_str


class AgentEventRenderer:
    """Renders agent events with Rich styling.

    Usage:
        renderer = AgentEventRenderer()
        renderer.render_header("AGENT TITLE", "Subtitle description")

        async for event in agent.run_stream(task):
            renderer.render_event(event)

        renderer.render_results_summary(answer, tools, turns, elapsed)
        renderer.render_token_metrics_table(metrics)
    """

    def __init__(self, config: DisplayConfig | None = None) -> None:
        self.config = config or DisplayConfig()
        self._current_ttft: float | None = None
        self._turn = 1

    # =========================================================================
    # Event rendering methods
    # =========================================================================

    def render_text_delta(self, event: TextDeltaEvent) -> None:
        """Stream text character-by-character (preserves real-time feel)."""
        sys.stdout.write(str(event.delta))
        sys.stdout.flush()

    def render_block_extracted(self, event: BlockExtractedEvent) -> None:
        """Display extracted block notification."""
        block = event.block
        console.print(f"\n[dim][Block: {block.metadata.block_type} id={block.metadata.id}][/dim]")

    def render_tool_call(self, event: ToolCallEvent) -> None:
        """Display tool call with parameters."""
        console.print(f"\n[bold {self.config.tool_style}][Tool call: {event.tool_name}][/]")
        params_str = truncate(str(event.parameters), self.config.truncate_params_at)
        console.print(f"[dim]  Parameters: {params_str}[/dim]")

    def render_tool_started(self, event: ToolStartedEvent) -> None:
        """Display tool started in background."""
        console.print(f"[{self.config.tool_style}][Tool {event.tool_name} started in background...][/]")

    def render_tool_result(self, event: ToolCallResultEvent) -> None:
        """Display tool result with status."""
        if event.result.success:
            style = self.config.success_style
            status = "SUCCESS"
            result_str = truncate(str(event.result.result), self.config.truncate_result_at)
        else:
            style = self.config.error_style
            status = "ERROR"
            result_str = truncate(str(event.result.error), self.config.truncate_result_at)

        console.print(f"\n[bold {style}][Tool result ({status}): {result_str}][/]")

        if event.injected:
            console.print("[dim italic][Result injected mid-stream][/]")

    def render_stream_cancelled(self, event: StreamCancelledEvent) -> None:
        """Display stream cancellation notification."""
        console.print(f"\n[{self.config.cancelled_style}][Stream cancelled: {event.reason}][/]")
        self._turn += 1
        console.print(f"\n[bold]--- Turn {self._turn} ---[/]\n")

    def render_llm_start(self, event: LLMCallStartEvent) -> None:
        """Display LLM call start."""
        console.print(f"\n[{self.config.llm_style}][LLM Call {event.call_number} started][/]")
        self._current_ttft = None

    def render_llm_first_token(self, event: LLMFirstTokenEvent) -> None:
        """Display time to first token."""
        self._current_ttft = event.ttft
        console.print(f"[dim][TTFT: {event.ttft * 1000:.0f}ms][/dim]")

    def render_llm_end(self, event: LLMCallEndEvent) -> None:
        """Display LLM call completion."""
        if event.cancelled:
            style = self.config.cancelled_style
            status = "cancelled"
        else:
            style = self.config.llm_style
            status = "completed"

        console.print(
            f"[{style}][LLM Call {event.call_number} {status}: "
            f"{event.total_tokens} tokens, {event.duration:.2f}s][/]"
        )

    def render_answer(self, event: AnswerEvent) -> None:
        """Display final answer (handled separately in summary)."""
        # Answer is typically displayed in the results summary
        pass

    def render_event(self, event: Any) -> bool:
        """Unified event dispatcher - handles any event type.

        Returns:
            True if event was handled, False otherwise
        """
        # Import here to avoid circular imports
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
        from hother.streamblocks import BlockExtractedEvent, TextDeltaEvent

        if isinstance(event, TextDeltaEvent):
            self.render_text_delta(event)
        elif isinstance(event, BlockExtractedEvent):
            self.render_block_extracted(event)
        elif isinstance(event, ToolCallEvent):
            self.render_tool_call(event)
        elif isinstance(event, ToolStartedEvent):
            self.render_tool_started(event)
        elif isinstance(event, ToolCallResultEvent):
            self.render_tool_result(event)
        elif isinstance(event, StreamCancelledEvent):
            self.render_stream_cancelled(event)
        elif isinstance(event, LLMCallStartEvent):
            self.render_llm_start(event)
        elif isinstance(event, LLMFirstTokenEvent):
            self.render_llm_first_token(event)
        elif isinstance(event, LLMCallEndEvent):
            self.render_llm_end(event)
        elif isinstance(event, AnswerEvent):
            self.render_answer(event)
        else:
            return False
        return True

    # =========================================================================
    # Section rendering methods
    # =========================================================================

    def render_header(self, title: str, subtitle: str | None = None) -> None:
        """Display agent header panel."""
        content = f"[bold]{title}[/]"
        if subtitle:
            content += f"\n[dim]{subtitle}[/]"

        console.print(Panel(content, border_style=self.config.header_border_style, box=box.DOUBLE))
        console.print()

    def render_task(self, task: str) -> None:
        """Display the task being executed."""
        console.print(f"[bold]Task:[/] {task}")
        console.print()
        console.print("[dim]--- Streaming Output ---[/dim]")
        console.print()

    def render_results_summary(
        self,
        final_answer: str,
        tools_called: int,
        turns: int,
        elapsed: float,
    ) -> None:
        """Display results summary table."""
        console.print()
        console.print()

        table = Table(
            title="Results",
            show_header=False,
            box=box.ROUNDED,
            border_style=self.config.success_style,
        )
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="bold")

        table.add_row("Final Answer", final_answer)
        table.add_row("Tools called", str(tools_called))
        table.add_row("Turns", str(turns))
        table.add_row("Time", f"{elapsed:.2f}s")

        console.print(table)

    def render_token_metrics_summary(
        self,
        llm_calls: int,
        total_prompt_tokens: int,
        total_completion_tokens: int,
        total_tokens: int,
        total_cached_tokens: int = 0,
        total_thoughts_tokens: int = 0,
    ) -> None:
        """Display token metrics summary."""
        console.print()

        table = Table(
            title="Token Metrics",
            show_header=False,
            box=box.ROUNDED,
            border_style=self.config.metrics_border_style,
        )
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="bold", justify="right")

        table.add_row("LLM API calls", str(llm_calls))
        table.add_row("Total prompt tokens", str(total_prompt_tokens))
        table.add_row("Total completion tokens", str(total_completion_tokens))
        table.add_row("Total cached tokens", str(total_cached_tokens))
        table.add_row("Total thoughts tokens", str(total_thoughts_tokens))
        table.add_row("Total tokens", str(total_tokens))

        console.print(table)

    def render_token_metrics_table(self, metrics: list[dict[str, Any]]) -> None:
        """Render per-call token breakdown as a Rich table."""
        console.print()

        table = Table(
            title="Per-Call Breakdown",
            box=box.ROUNDED,
            border_style=self.config.metrics_border_style,
        )

        table.add_column("Call", style="cyan", justify="right")
        table.add_column("TTFT", style="yellow", justify="right")
        table.add_column("Prompt", justify="right")
        table.add_column("Cached", justify="right")
        table.add_column("Compl", justify="right")
        table.add_column("Thoughts", justify="right")
        table.add_column("Total", style="bold", justify="right")
        table.add_column("Duration", justify="right")
        table.add_column("Status")

        for m in metrics:
            ttft = m.get("ttft")
            ttft_str = f"{ttft * 1000:.0f}ms" if ttft is not None else "N/A"

            if m.get("cancelled", False):
                status = f"[{self.config.cancelled_style}]cancelled[/]"
            else:
                status = f"[{self.config.success_style}]completed[/]"

            table.add_row(
                str(m.get("call", "")),
                ttft_str,
                str(m.get("prompt_tokens", 0)),
                str(m.get("cached_tokens", 0)),
                str(m.get("completion_tokens", 0)),
                str(m.get("thoughts_tokens", 0)),
                str(m.get("total_tokens", 0)),
                f"{m.get('duration', 0):.2f}s",
                status,
            )

        console.print(table)

    def render_comparison_table(
        self,
        sb_label: str,
        pai_label: str,
        metrics: list[tuple[str, str, str]],
    ) -> None:
        """Render comparison table between two agents.

        Args:
            sb_label: Label for StreamBlocks column
            pai_label: Label for Pydantic AI column
            metrics: List of (metric_name, sb_value, pai_value) tuples
        """
        console.print()

        table = Table(
            title="Comparison Summary",
            box=box.DOUBLE,
            border_style=self.config.comparison_border_style,
        )

        table.add_column("Metric", style="bold")
        table.add_column(sb_label, style="green", justify="right")
        table.add_column(pai_label, style="blue", justify="right")

        for metric, sb_val, pai_val in metrics:
            table.add_row(metric, sb_val, pai_val)

        console.print(table)

    def render_notes(self, notes: list[str]) -> None:
        """Display notes section."""
        console.print()
        for note in notes:
            console.print(f"[dim]{note}[/dim]")

    def reset_turn_counter(self) -> None:
        """Reset turn counter for a new run."""
        self._turn = 1


# Convenience functions for quick usage
def print_header(title: str, subtitle: str | None = None) -> None:
    """Quick header print."""
    renderer = AgentEventRenderer()
    renderer.render_header(title, subtitle)


def print_comparison(
    sb_label: str,
    pai_label: str,
    metrics: list[tuple[str, str, str]],
) -> None:
    """Quick comparison table print."""
    renderer = AgentEventRenderer()
    renderer.render_comparison_table(sb_label, pai_label, metrics)
