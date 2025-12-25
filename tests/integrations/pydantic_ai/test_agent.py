"""Tests for BlockAwareAgent PydanticAI integration."""

from __future__ import annotations

import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic_ai import Agent

from hother.streamblocks import DelimiterPreambleSyntax, Registry


class TestAgentImportError:
    """Test ImportError handling when pydantic-ai is not installed."""

    def test_import_error_when_pydantic_ai_missing(self) -> None:
        """Test that ImportError is raised when pydantic-ai not installed.

        This covers lines 9-11 of agent.py.
        """
        import importlib

        # Store original modules
        original_agent_module = sys.modules.get("hother.streamblocks.integrations.pydantic_ai.agent")
        original_pydantic_ai = sys.modules.get("pydantic_ai")

        # Remove modules to force reimport
        if "hother.streamblocks.integrations.pydantic_ai.agent" in sys.modules:
            del sys.modules["hother.streamblocks.integrations.pydantic_ai.agent"]

        # Mock pydantic_ai to raise ImportError
        def mock_import(name: str, *args: Any, **kwargs: Any) -> Any:
            if name == "pydantic_ai":
                raise ImportError("Mock: pydantic-ai not installed")
            return original_import(name, *args, **kwargs)

        original_import = __builtins__["__import__"]

        try:
            with patch.dict("sys.modules", {"pydantic_ai": None}):
                with patch("builtins.__import__", side_effect=mock_import):
                    with pytest.raises(ImportError, match="pydantic-ai is required"):
                        importlib.import_module("hother.streamblocks.integrations.pydantic_ai.agent")
        finally:
            # Restore original modules
            if original_agent_module is not None:
                sys.modules["hother.streamblocks.integrations.pydantic_ai.agent"] = original_agent_module
            if original_pydantic_ai is not None:
                sys.modules["pydantic_ai"] = original_pydantic_ai


class TestBlockAwareAgentInit:
    """Tests for BlockAwareAgent initialization."""

    def test_init_with_model_string(self) -> None:
        """Test initialization with a model string."""
        from hother.streamblocks.integrations.pydantic_ai.agent import BlockAwareAgent

        registry = Registry(syntax=DelimiterPreambleSyntax())

        # Create a proper mock agent instance
        mock_agent = MagicMock(spec=Agent)

        with (
            patch.object(Agent, "__new__", return_value=mock_agent),
            patch.object(Agent, "__init__", return_value=None),
        ):
            agent = BlockAwareAgent(
                registry=registry,
                model="test:model",
                system_prompt="Test prompt",
            )

            assert agent.registry is registry
            assert agent.agent is mock_agent

    def test_init_with_existing_agent(self) -> None:
        """Test initialization with an existing Agent instance."""
        from hother.streamblocks.integrations.pydantic_ai.agent import BlockAwareAgent

        registry = Registry(syntax=DelimiterPreambleSyntax())

        # Create a mock that will pass isinstance check
        existing_agent = MagicMock(spec=Agent)
        # Make isinstance work by setting __class__
        existing_agent.__class__ = Agent

        agent = BlockAwareAgent(
            registry=registry,
            model=existing_agent,
        )

        assert agent.agent is existing_agent
        assert agent.registry is registry

    def test_init_with_default_model(self) -> None:
        """Test initialization with default model (None)."""
        from hother.streamblocks.integrations.pydantic_ai.agent import BlockAwareAgent

        registry = Registry(syntax=DelimiterPreambleSyntax())

        mock_agent = MagicMock(spec=Agent)

        with (
            patch.object(Agent, "__new__", return_value=mock_agent),
            patch.object(Agent, "__init__", return_value=None),
        ):
            agent = BlockAwareAgent(
                registry=registry,
                system_prompt="Test",
            )

            # The agent should be created
            assert agent.agent is mock_agent

    def test_init_creates_processor(self) -> None:
        """Test that initialization creates an AgentStreamProcessor."""
        from hother.streamblocks.integrations.pydantic_ai.agent import BlockAwareAgent
        from hother.streamblocks.integrations.pydantic_ai.processor import AgentStreamProcessor

        registry = Registry(syntax=DelimiterPreambleSyntax())

        mock_agent = MagicMock(spec=Agent)

        with (
            patch.object(Agent, "__new__", return_value=mock_agent),
            patch.object(Agent, "__init__", return_value=None),
        ):
            agent = BlockAwareAgent(registry=registry, model="test:model")

            assert agent.processor is not None
            assert isinstance(agent.processor, AgentStreamProcessor)


class TestBlockAwareAgentRunMethods:
    """Tests for BlockAwareAgent run methods."""

    @pytest.mark.asyncio
    async def test_run_delegates_to_agent(self) -> None:
        """Test that run() delegates to the underlying agent."""
        from hother.streamblocks.integrations.pydantic_ai.agent import BlockAwareAgent

        registry = Registry(syntax=DelimiterPreambleSyntax())

        mock_agent = MagicMock(spec=Agent)
        mock_agent.run = AsyncMock(return_value="response")

        with (
            patch.object(Agent, "__new__", return_value=mock_agent),
            patch.object(Agent, "__init__", return_value=None),
        ):
            agent = BlockAwareAgent(registry=registry, model="test:model")

            result = await agent.run("test prompt")

            mock_agent.run.assert_called_once_with(
                "test prompt",
                message_history=None,
                deps=None,
            )
            assert result == "response"

    @pytest.mark.asyncio
    async def test_run_with_history_and_deps(self) -> None:
        """Test run() with message history and dependencies."""
        from hother.streamblocks.integrations.pydantic_ai.agent import BlockAwareAgent

        registry = Registry(syntax=DelimiterPreambleSyntax())

        mock_agent = MagicMock(spec=Agent)
        mock_agent.run = AsyncMock(return_value="response")

        with (
            patch.object(Agent, "__new__", return_value=mock_agent),
            patch.object(Agent, "__init__", return_value=None),
        ):
            agent = BlockAwareAgent(registry=registry, model="test:model")

            history = [{"role": "user", "content": "hi"}]
            deps = {"key": "value"}
            await agent.run("prompt", message_history=history, deps=deps)

            mock_agent.run.assert_called_once_with(
                "prompt",
                message_history=history,
                deps=deps,
            )

    def test_run_sync_delegates_to_agent(self) -> None:
        """Test that run_sync() delegates to the underlying agent."""
        from hother.streamblocks.integrations.pydantic_ai.agent import BlockAwareAgent

        registry = Registry(syntax=DelimiterPreambleSyntax())

        mock_agent = MagicMock(spec=Agent)
        mock_agent.run_sync = MagicMock(return_value="sync response")

        with (
            patch.object(Agent, "__new__", return_value=mock_agent),
            patch.object(Agent, "__init__", return_value=None),
        ):
            agent = BlockAwareAgent(registry=registry, model="test:model")

            result = agent.run_sync("test prompt")

            mock_agent.run_sync.assert_called_once_with(
                "test prompt",
                message_history=None,
                deps=None,
            )
            assert result == "sync response"


class TestBlockAwareAgentGetattr:
    """Tests for BlockAwareAgent attribute forwarding."""

    def test_getattr_forwards_to_agent(self) -> None:
        """Test that unknown attributes are forwarded to the underlying agent."""
        from hother.streamblocks.integrations.pydantic_ai.agent import BlockAwareAgent

        registry = Registry(syntax=DelimiterPreambleSyntax())

        mock_agent = MagicMock(spec=Agent)
        mock_agent.some_property = "agent property"
        mock_agent.some_method = MagicMock(return_value="method result")

        with (
            patch.object(Agent, "__new__", return_value=mock_agent),
            patch.object(Agent, "__init__", return_value=None),
        ):
            agent = BlockAwareAgent(registry=registry, model="test:model")

            # Access property
            assert agent.some_property == "agent property"

            # Call method
            assert agent.some_method() == "method result"

    def test_getattr_accesses_own_attributes_first(self) -> None:
        """Test that own attributes are accessed before forwarding."""
        from hother.streamblocks.integrations.pydantic_ai.agent import BlockAwareAgent

        registry = Registry(syntax=DelimiterPreambleSyntax())

        mock_agent = MagicMock(spec=Agent)

        with (
            patch.object(Agent, "__new__", return_value=mock_agent),
            patch.object(Agent, "__init__", return_value=None),
        ):
            agent = BlockAwareAgent(registry=registry, model="test:model")

            # These should access BlockAwareAgent's own attributes
            assert agent.registry is registry
            assert agent.processor is not None


class TestBlockAwareAgentRunWithBlocks:
    """Tests for run_with_blocks streaming method."""

    @pytest.mark.asyncio
    async def test_run_with_blocks_yields_events(self) -> None:
        """Test that run_with_blocks yields events from processor."""
        from hother.streamblocks.integrations.pydantic_ai.agent import BlockAwareAgent

        registry = Registry(syntax=DelimiterPreambleSyntax())

        # Create mock stream_text that yields deltas
        async def mock_stream_text(delta: bool = False) -> Any:
            yield "Hello "
            yield "world!"

        # Create mock stream result
        mock_stream_result = MagicMock()
        mock_stream_result.stream_text = mock_stream_text

        # Create async context manager for run_stream
        mock_run_stream = MagicMock()
        mock_run_stream.__aenter__ = AsyncMock(return_value=mock_stream_result)
        mock_run_stream.__aexit__ = AsyncMock(return_value=None)

        mock_agent = MagicMock(spec=Agent)
        mock_agent.run_stream = MagicMock(return_value=mock_run_stream)

        with (
            patch.object(Agent, "__new__", return_value=mock_agent),
            patch.object(Agent, "__init__", return_value=None),
        ):
            agent = BlockAwareAgent(registry=registry, model="test:model")

            events: list[Any] = []
            async for event in agent.run_with_blocks("test prompt"):
                events.append(event)

            # Should have processed some events (at least stream lifecycle events)
            assert len(events) > 0

    @pytest.mark.asyncio
    async def test_run_with_blocks_passes_kwargs(self) -> None:
        """Test that run_with_blocks passes kwargs to run_stream."""
        from hother.streamblocks.integrations.pydantic_ai.agent import BlockAwareAgent

        registry = Registry(syntax=DelimiterPreambleSyntax())

        # Create empty stream
        async def mock_stream_text(delta: bool = False) -> Any:
            return
            yield  # Make it an async generator

        mock_stream_result = MagicMock()
        mock_stream_result.stream_text = mock_stream_text

        mock_run_stream = MagicMock()
        mock_run_stream.__aenter__ = AsyncMock(return_value=mock_stream_result)
        mock_run_stream.__aexit__ = AsyncMock(return_value=None)

        mock_agent = MagicMock(spec=Agent)
        mock_agent.run_stream = MagicMock(return_value=mock_run_stream)

        with (
            patch.object(Agent, "__new__", return_value=mock_agent),
            patch.object(Agent, "__init__", return_value=None),
        ):
            agent = BlockAwareAgent(registry=registry, model="test:model")

            history = [{"role": "user", "content": "hi"}]
            deps = {"key": "value"}

            # Consume the generator
            async for _ in agent.run_with_blocks(
                "test prompt",
                message_history=history,
                deps=deps,
                custom_arg="value",
            ):
                pass

            # Verify run_stream was called with the right args
            mock_agent.run_stream.assert_called_once_with(
                "test prompt",
                message_history=history,
                deps=deps,
                custom_arg="value",
            )
