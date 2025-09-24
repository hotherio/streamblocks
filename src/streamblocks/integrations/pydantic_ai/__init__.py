"""PydanticAI integration for StreamBlocks.

This module provides transparent integration between PydanticAI agents and StreamBlocks,
allowing agents to generate structured blocks that are extracted in real-time during streaming.
"""

from streamblocks.integrations.pydantic_ai.agent import BlockAwareAgent
from streamblocks.integrations.pydantic_ai.processor import AgentStreamProcessor

__all__ = [
    "BlockAwareAgent",
    "AgentStreamProcessor",
]