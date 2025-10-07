"""PydanticAI integration for StreamBlocks.

This module provides transparent integration between PydanticAI agents and StreamBlocks,
allowing agents to generate structured blocks that are extracted in real-time during streaming.
"""

from hother.streamblocks.integrations.pydantic_ai.agent import BlockAwareAgent
from hother.streamblocks.integrations.pydantic_ai.processor import AgentStreamProcessor

__all__ = [
    "AgentStreamProcessor",
    "BlockAwareAgent",
]
