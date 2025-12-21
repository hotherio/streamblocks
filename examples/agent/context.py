"""RunContext for Pydantic AI-style dependency injection.

Provides typed access to dependencies within tool functions,
similar to Pydantic AI's RunContext pattern.

Example:
    @dataclass
    class AppDeps:
        db_url: str
        api_key: str

    agent = Agent[AppDeps](model="gemini-2.5-flash")

    @agent.tool
    def fetch_user(ctx: RunContext[AppDeps], user_id: int) -> dict:
        # Access typed deps via ctx.deps
        return {"id": user_id, "db": ctx.deps.db_url}

    result = await agent.run("Get user 123", deps=AppDeps(...))
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RunContext[TDeps]:
    """Context passed to tools during execution.

    Provides:
    - Type-safe access to dependencies
    - Information about the current tool execution
    - Retry count for error handling

    Attributes:
        deps: The dependencies object passed to agent.run()
        retry: Current retry attempt (0 = first attempt)
        tool_name: Name of the tool being executed
        tool_id: Unique ID of this tool call (from Action block)
    """

    deps: TDeps
    retry: int = 0
    tool_name: str | None = None
    tool_id: str | None = None

    def with_retry(self, retry: int) -> RunContext[TDeps]:
        """Create a new context with updated retry count."""
        return RunContext(
            deps=self.deps,
            retry=retry,
            tool_name=self.tool_name,
            tool_id=self.tool_id,
        )
