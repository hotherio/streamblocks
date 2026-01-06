"""Block definitions for the StreamBlocks Agent.

Only 2 block types are needed:
- ToolCall: Tool calls with YAML parameters
- FinalAnswer: Agent's final response

Natural text streaming via TextDeltaEvent serves as reasoning -
no explicit Thought block required (LLMs already think internally).
"""

from __future__ import annotations

from typing import Any, Self

import yaml
from pydantic import Field

from hother.streamblocks.core.models import Block
from hother.streamblocks.core.types import BaseContent, BaseMetadata


class ToolCallMetadata(BaseMetadata):
    """Metadata for tool call blocks.

    Attributes:
        id: Unique identifier for this tool call
        block_type: Always "tool_call"
        tool_name: Name of the tool to execute
        timeout: Optional timeout in seconds for tool execution
    """

    tool_name: str
    timeout: float | None = None


class ToolCallContent(BaseContent):
    """Content for tool call blocks - YAML-encoded parameters.

    Attributes:
        raw_content: The raw YAML text
        parameters: Parsed parameters as a dictionary
    """

    parameters: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def parse(cls, raw_text: str) -> Self:
        """Parse YAML parameters from raw content."""
        try:
            params: dict[str, Any] = yaml.safe_load(raw_text) or {}
        except yaml.YAMLError:
            # If YAML parsing fails, store raw text with no parameters
            params = {}

        return cls(raw_content=raw_text, parameters=params)


# Block type alias for tool calls
ToolCall = Block[ToolCallMetadata, ToolCallContent]

# Add documentation example for ToolCall block
ToolCall.__doc_example__ = """When you need to use a tool, emit a tool_call block:

!!start
---
id: tool_call_<number>
block_type: tool_call
tool_name: <tool_name>
---
<YAML parameters>
!!end"""


class FinalAnswerMetadata(BaseMetadata):
    """Metadata for final answer blocks.

    Attributes:
        id: Unique identifier for this answer
        block_type: Always "final_answer"
        tools_called: Number of tools called during execution
    """

    tools_called: int = 0


class FinalAnswerContent(BaseContent):
    """Content for final answer blocks.

    Attributes:
        raw_content: The raw answer text
        answer: Cleaned answer text
    """

    answer: str = ""

    @classmethod
    def parse(cls, raw_text: str) -> Self:
        """Parse the final answer from raw content."""
        return cls(raw_content=raw_text, answer=raw_text.strip())


# Block type alias for final answers
FinalAnswer = Block[FinalAnswerMetadata, FinalAnswerContent]

# Add documentation example for FinalAnswer block
FinalAnswer.__doc_example__ = """When you have the final answer, emit a final_answer block:

!!start
---
id: answer_1
block_type: final_answer
tools_called: <number>
---
<Your final answer here>
!!end"""


class WaitMetadata(BaseMetadata):
    """Metadata for wait blocks.

    Attributes:
        id: Unique identifier for this wait block
        block_type: Always "wait"
    """

    # No additional metadata needed


class WaitContent(BaseContent):
    """Content for wait blocks - list of tool IDs to wait for.

    Attributes:
        raw_content: The raw YAML text
        tool_ids: List of tool call IDs to wait for
    """

    tool_ids: list[str] = Field(default_factory=list)

    @classmethod
    def parse(cls, raw_text: str) -> Self:
        """Parse tool IDs from YAML list."""
        try:
            parsed = yaml.safe_load(raw_text)
            tool_ids = [str(tid) for tid in parsed] if isinstance(parsed, list) else []
        except yaml.YAMLError:
            tool_ids = []

        return cls(raw_content=raw_text, tool_ids=tool_ids)


# Block type alias for wait blocks
Wait = Block[WaitMetadata, WaitContent]

# Add documentation example for Wait block
Wait.__doc_example__ = """When you need results from specific tools before continuing (for example, when one tool's output is needed as input to another), emit a wait block:

!!start
---
id: wait_<number>
block_type: wait
---
- tool_call_1
- tool_call_2
!!end

This tells the system to wait for those specific tools to complete before giving you their results. Use this when:
- You need product IDs from search_products before calling create_order
- One tool's output is required as input for another tool
- You want to ensure you have the data before proceeding"""
