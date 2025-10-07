"""Block definitions and content models for StreamBlocks."""

from hother.streamblocks.blocks.base import BaseContent
from hother.streamblocks.blocks.files import (
    FileContentContent,
    FileContentDefinition,
    FileContentMetadata,
    FileOperationsContent,
    FileOperationsDefinition,
    FileOperationsMetadata,
)
from hother.streamblocks.blocks.interactive import (
    ChoiceContent,
    ChoiceMetadata,
    ConfirmContent,
    ConfirmMetadata,
    FormContent,
    FormField,
    FormMetadata,
    InputContent,
    InputMetadata,
    InteractiveContent,
    InteractiveMetadata,
    MultiChoiceContent,
    MultiChoiceMetadata,
    RankingContent,
    RankingMetadata,
    ScaleContent,
    ScaleMetadata,
    YesNoContent,
    YesNoMetadata,
)
from hother.streamblocks.blocks.memory import MemoryContent, MemoryMetadata
from hother.streamblocks.blocks.message import MessageContent, MessageMetadata
from hother.streamblocks.blocks.patch import PatchContent, PatchMetadata
from hother.streamblocks.blocks.toolcall import ToolCallContent, ToolCallMetadata
from hother.streamblocks.blocks.visualization import VisualizationContent, VisualizationMetadata

__all__ = [
    # Base
    "BaseContent",
    "ChoiceContent",
    "ChoiceMetadata",
    "ConfirmContent",
    "ConfirmMetadata",
    "FileContentContent",
    "FileContentDefinition",
    "FileContentMetadata",
    # File operations
    "FileOperationsContent",
    "FileOperationsDefinition",
    "FileOperationsMetadata",
    "FormContent",
    "FormField",
    "FormMetadata",
    "InputContent",
    "InputMetadata",
    "InteractiveContent",
    # Interactive base
    "InteractiveMetadata",
    # Memory
    "MemoryContent",
    "MemoryMetadata",
    # Message
    "MessageContent",
    "MessageMetadata",
    "MultiChoiceContent",
    "MultiChoiceMetadata",
    # Patch
    "PatchContent",
    "PatchMetadata",
    "RankingContent",
    "RankingMetadata",
    "ScaleContent",
    "ScaleMetadata",
    # Tool calling
    "ToolCallContent",
    "ToolCallMetadata",
    # Visualization
    "VisualizationContent",
    "VisualizationMetadata",
    "YesNoContent",
    # Interactive specific
    "YesNoMetadata",
]
