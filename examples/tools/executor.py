"""Tool executor for running tools from blocks."""

from __future__ import annotations

import asyncio
import time
import traceback
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine


@dataclass
class ToolResult:
    """Result from tool execution."""

    success: bool
    result: Any | None = None
    error: str | None = None
    execution_time: float = 0.0


class ToolExecutor:
    """Executes tools registered by name."""

    def __init__(self) -> None:
        self.tools: dict[str, Callable[..., Any]] = {}
        self.async_tools: dict[str, Callable[..., Coroutine[Any, Any, Any]]] = {}

    def register_tool(self, name: str, func: Callable[..., Any], is_async: bool = False) -> None:
        """Register a tool function."""
        if is_async:
            self.async_tools[name] = func
        else:
            self.tools[name] = func

    def register_class_tools(self, prefix: str, tool_class: Any) -> None:
        """Register all public methods from a class as tools."""
        for method_name in dir(tool_class):
            if not method_name.startswith("_"):
                method = getattr(tool_class, method_name)
                if callable(method):
                    tool_name = f"{prefix}.{method_name}"
                    is_async = asyncio.iscoroutinefunction(method)
                    self.register_tool(tool_name, method, is_async)

    async def execute(self, tool_name: str, parameters: dict[str, Any]) -> ToolResult:
        """Execute a tool by name with parameters."""
        start_time = time.time()

        try:
            if tool_name in self.tools:
                # Sync tool
                result = self.tools[tool_name](**parameters)
                execution_time = time.time() - start_time
                return ToolResult(success=True, result=result, execution_time=execution_time)
            if tool_name in self.async_tools:
                # Async tool
                result = await self.async_tools[tool_name](**parameters)
                execution_time = time.time() - start_time
                return ToolResult(success=True, result=result, execution_time=execution_time)
            return ToolResult(
                success=False, error=f"Unknown tool: {tool_name}", execution_time=time.time() - start_time
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"{type(e).__name__}: {e!s}\n{traceback.format_exc()}",
                execution_time=time.time() - start_time,
            )

    def list_tools(self) -> list[str]:
        """List all available tool names."""
        return sorted(list(self.tools.keys()) + list(self.async_tools.keys()))
