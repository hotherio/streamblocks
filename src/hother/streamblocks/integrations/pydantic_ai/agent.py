"""BlockAware PydanticAI agent for StreamBlocks integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

try:
    from pydantic_ai import Agent
except ImportError as e:
    msg = "pydantic-ai is required for PydanticAI integration. Install with: pip install pydantic-ai"
    raise ImportError(msg) from e

from hother.streamblocks.integrations.pydantic_ai.processor import AgentStreamProcessor

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, AsyncIterator

    from hother.streamblocks.core.registry import Registry
    from hother.streamblocks.core.types import BaseEvent


class BlockAwareAgent:
    """PydanticAI agent that generates StreamBlocks-compatible output.

    This wrapper makes a PydanticAI agent aware of StreamBlocks syntaxes,
    allowing it to generate structured blocks that can be extracted in real-time.
    """

    def __init__(
        self,
        registry: Registry,
        model: str | Agent | None = None,
        system_prompt: str | None = None,
        **agent_kwargs: Any,
    ) -> None:
        """Initialize a block-aware agent.

        Args:
            registry: StreamBlocks registry containing syntax definitions
            model: Model name (e.g., 'openai:gpt-4o') or existing Agent instance
            system_prompt: System prompt for the agent (required if creating new agent)
            **agent_kwargs: Additional arguments to pass to Agent constructor
        """
        # Create or use existing agent
        if isinstance(model, Agent):
            self.agent = model
        else:
            # Use provided system_prompt
            if system_prompt:
                agent_kwargs["system_prompt"] = system_prompt
            self.agent = Agent(model or "openai:gpt-4o", **agent_kwargs)

        # Setup registry and processor
        self.registry = registry
        self.processor = AgentStreamProcessor(registry)

    async def run_with_blocks(
        self,
        user_prompt: str,
        message_history: Any = None,
        deps: Any = None,
        **kwargs: Any,
    ) -> AsyncGenerator[str | BaseEvent]:
        """Run the agent and stream blocks in real-time.

        Args:
            user_prompt: The user's prompt to the agent
            message_history: Optional conversation history
            deps: Optional dependencies for the agent
            **kwargs: Additional arguments for agent.run_stream()

        Yields:
            Mixed stream of:
            - Original text chunks (if emit_original_events=True)
            - Event objects as blocks are detected and extracted
        """

        # Start agent streaming
        async with self.agent.run_stream(
            user_prompt, message_history=message_history, deps=deps, **kwargs
        ) as stream_result:
            # Create text stream from agent
            # Use PydanticAI's native delta streaming feature
            async def agent_text_stream() -> AsyncIterator[str]:
                async for delta_text in stream_result.stream_text(delta=True):
                    yield delta_text

            # Process through StreamBlocks
            async for event in self.processor.process_agent_stream(agent_text_stream()):
                yield event

    async def run(
        self,
        user_prompt: str,
        message_history: Any = None,
        deps: Any = None,
        **kwargs: Any,
    ) -> Any:
        """Run the agent without block extraction (standard PydanticAI interface).

        This method provides compatibility with the standard PydanticAI Agent interface.

        Args:
            user_prompt: The user's prompt to the agent
            message_history: Optional conversation history
            deps: Optional dependencies for the agent
            **kwargs: Additional arguments for agent.run()

        Returns:
            The agent's response
        """
        return await self.agent.run(user_prompt, message_history=message_history, deps=deps, **kwargs)

    def run_sync(
        self,
        user_prompt: str,
        message_history: Any = None,
        deps: Any = None,
        **kwargs: Any,
    ) -> Any:
        """Run the agent synchronously without block extraction.

        This method provides compatibility with the standard PydanticAI Agent interface.

        Args:
            user_prompt: The user's prompt to the agent
            message_history: Optional conversation history
            deps: Optional dependencies for the agent
            **kwargs: Additional arguments for agent.run_sync()

        Returns:
            The agent's response
        """
        return self.agent.run_sync(user_prompt, message_history=message_history, deps=deps, **kwargs)

    def __getattr__(self, name: str) -> Any:
        """Forward unknown attributes to the underlying agent.

        This allows the BlockAwareAgent to act as a transparent wrapper.

        Args:
            name: Attribute name

        Returns:
            The attribute from the underlying agent
        """
        return getattr(self.agent, name)
