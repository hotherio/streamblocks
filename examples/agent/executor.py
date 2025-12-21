"""Tool executor with retry, timeout, and RunContext support.

Extends the basic ToolExecutor pattern with:
- Configurable retry logic per tool
- Timeout support with asyncio.wait_for
- RunContext injection for dependency injection
- Async and sync tool support
"""

from __future__ import annotations

import asyncio
import inspect
import time
import traceback
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, get_args, get_origin, get_type_hints

from pydantic import BaseModel

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

    from examples.agent.context import RunContext


def _convert_value(value: Any, annotation: type) -> Any:
    """Convert a single value to match the annotation type.

    Handles:
    - Pydantic BaseModel: dict -> Model(**dict)
    - list[Model]: [dict, ...] -> [Model(**dict), ...]
    - Other types: return as-is
    """
    if value is None:
        return value

    origin = get_origin(annotation)

    # Handle list[Model]
    if origin is list and isinstance(value, list):
        args = get_args(annotation)
        if args:
            item_type = args[0]
            # Check if item type is a Pydantic model
            if isinstance(item_type, type) and issubclass(item_type, BaseModel):
                return [item_type(**item) if isinstance(item, dict) else item for item in value]
        return value

    # Handle Pydantic BaseModel
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        if isinstance(value, dict):
            return annotation(**value)

    return value


def _convert_parameters(func: Callable[..., Any], parameters: dict[str, Any]) -> dict[str, Any]:
    """Convert dict parameters to Pydantic models based on function type hints.

    This enables Pydantic AI-compatible behavior where tool functions receive
    properly typed Pydantic objects instead of raw dicts from YAML parsing.

    Args:
        func: The tool function with type hints
        parameters: Raw parameters from YAML parsing

    Returns:
        Parameters with dicts converted to Pydantic models where applicable
    """
    try:
        type_hints = get_type_hints(func)
    except Exception:
        # If we can't get type hints, return parameters as-is
        return parameters

    converted: dict[str, Any] = {}

    for param_name, param_value in parameters.items():
        if param_name not in type_hints:
            converted[param_name] = param_value
            continue

        annotation = type_hints[param_name]
        converted[param_name] = _convert_value(param_value, annotation)

    return converted


@dataclass
class ToolResult:
    """Result from tool execution.

    Attributes:
        success: Whether the tool executed successfully
        result: The return value (if success)
        error: Error message (if failure)
        execution_time: Time taken in seconds
        retries_used: Number of retries before success/failure
    """

    success: bool
    result: Any | None = None
    error: str | None = None
    execution_time: float = 0.0
    retries_used: int = 0


@dataclass
class ToolDefinition:
    """Definition of a registered tool.

    Attributes:
        name: Tool name (used in Action blocks)
        description: Tool description (from docstring)
        func: The callable function
        is_async: Whether the function is async
        takes_context: Whether first param is RunContext
        timeout: Default timeout in seconds
        retries: Number of retries on failure
        params_schema: Parameter schema extracted from type hints
    """

    name: str
    description: str
    func: Callable[..., Any]
    is_async: bool
    takes_context: bool
    timeout: float
    retries: int
    params_schema: dict[str, dict[str, Any]] = field(default_factory=dict)


class ToolExecutor:
    """Executes tools with retry, timeout, and context support.

    Example:
        executor = ToolExecutor()

        @executor.register(timeout=30.0, retries=2)
        def calculate(expression: str) -> float:
            '''Evaluate a math expression.'''
            return eval(expression)

        result = await executor.execute("calculate", {"expression": "2 + 2"})
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(
        self,
        func: Callable[..., Any] | None = None,
        *,
        name: str | None = None,
        description: str | None = None,
        timeout: float = 30.0,
        retries: int = 0,
    ) -> Callable[..., Any]:
        """Register a tool function.

        Can be used as a decorator:
            @executor.register(timeout=30.0)
            def my_tool(x: int) -> str:
                ...

        Or called directly:
            executor.register(my_func, name="my_tool")
        """

        def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
            tool_name = name or f.__name__
            tool_desc = description or f.__doc__ or ""

            # Check if first parameter is RunContext
            sig = inspect.signature(f)
            params = list(sig.parameters.values())
            takes_context = False
            if params:
                first_param = params[0]
                # Check if annotation contains "RunContext"
                ann = first_param.annotation
                if ann != inspect.Parameter.empty:
                    ann_str = str(ann)
                    if "RunContext" in ann_str:
                        takes_context = True

            # Extract parameter schema (skip context param)
            params_schema = {}
            for param in params[1:] if takes_context else params:
                if param.annotation != inspect.Parameter.empty:
                    annotation = param.annotation
                    schema_entry: dict[str, Any] = {
                        "type": str(annotation),
                        "required": param.default == inspect.Parameter.empty,
                        "default": (None if param.default == inspect.Parameter.empty else param.default),
                    }

                    # Capture Pydantic model class for JSON schema generation
                    # Handle direct BaseModel subclass
                    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
                        schema_entry["model_class"] = annotation
                    # Handle list[Model] - extract the item type
                    elif hasattr(annotation, "__origin__") and annotation.__origin__ is list:
                        args = get_args(annotation)
                        if args and isinstance(args[0], type) and issubclass(args[0], BaseModel):
                            schema_entry["model_class"] = args[0]
                            schema_entry["is_list"] = True

                    params_schema[param.name] = schema_entry

            self._tools[tool_name] = ToolDefinition(
                name=tool_name,
                description=tool_desc.strip(),
                func=f,
                is_async=asyncio.iscoroutinefunction(f),
                takes_context=takes_context,
                timeout=timeout,
                retries=retries,
                params_schema=params_schema,
            )

            return f

        if func is not None:
            return decorator(func)
        return decorator

    def get(self, name: str) -> ToolDefinition | None:
        """Get a tool definition by name."""
        return self._tools.get(name)

    def list_tools(self) -> list[str]:
        """List all registered tool names."""
        return sorted(self._tools.keys())

    def get_tools_schema(self) -> list[dict[str, Any]]:
        """Get schema for all tools (for system prompt)."""
        schemas = []
        for tool in self._tools.values():
            schemas.append(
                {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.params_schema,
                }
            )
        return schemas

    async def execute(
        self,
        tool_name: str,
        parameters: dict[str, Any],
        context: RunContext[Any] | None = None,
        timeout_override: float | None = None,
    ) -> ToolResult:
        """Execute a tool by name with parameters.

        Args:
            tool_name: Name of the tool to execute
            parameters: Parameters to pass to the tool
            context: Optional RunContext for dependency injection
            timeout_override: Override the tool's default timeout

        Returns:
            ToolResult with success/failure info
        """
        tool = self._tools.get(tool_name)
        if not tool:
            return ToolResult(success=False, error=f"Unknown tool: {tool_name}")

        timeout = timeout_override or tool.timeout
        retries_remaining = tool.retries
        retries_used = 0

        while True:
            start_time = time.time()

            try:
                # Build arguments
                if tool.takes_context and context is not None:
                    # Update context with current retry count
                    ctx = context.with_retry(retries_used)
                    ctx.tool_name = tool_name
                    args = (ctx,)
                else:
                    args = ()

                # Convert dict parameters to Pydantic models based on type hints
                converted_params = _convert_parameters(tool.func, parameters)

                # Execute with timeout
                if tool.is_async:
                    coro: Coroutine[Any, Any, Any] = tool.func(*args, **converted_params)
                    result = await asyncio.wait_for(coro, timeout=timeout)
                else:
                    # Run sync function in thread pool
                    loop = asyncio.get_event_loop()
                    # Bind args and parameters to avoid closure issues
                    bound_args, bound_params = args, converted_params
                    result = await asyncio.wait_for(
                        loop.run_in_executor(None, lambda a=bound_args, p=bound_params: tool.func(*a, **p)),
                        timeout=timeout,
                    )

                execution_time = time.time() - start_time
                return ToolResult(
                    success=True,
                    result=result,
                    execution_time=execution_time,
                    retries_used=retries_used,
                )

            except TimeoutError:
                execution_time = time.time() - start_time
                if retries_remaining > 0:
                    retries_remaining -= 1
                    retries_used += 1
                    continue
                return ToolResult(
                    success=False,
                    error=f"Timeout after {timeout}s",
                    execution_time=execution_time,
                    retries_used=retries_used,
                )

            except Exception as e:
                execution_time = time.time() - start_time
                if retries_remaining > 0:
                    retries_remaining -= 1
                    retries_used += 1
                    continue
                return ToolResult(
                    success=False,
                    error=f"{type(e).__name__}: {e!s}\n{traceback.format_exc()}",
                    execution_time=execution_time,
                    retries_used=retries_used,
                )
