"""Content models for StreamBlocks."""

from streamblocks.content.base import BaseContent
from streamblocks.content.files import (
    FileContentContent,
    FileContentMetadata,
    FileOperationsContent,
    FileOperationsMetadata,
)
from streamblocks.content.interactive import (
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
from streamblocks.content.patch import PatchContent, PatchMetadata
from streamblocks.content.toolcall import ToolCallContent, ToolCallMetadata
from streamblocks.content.visualization import VisualizationContent, VisualizationMetadata
from streamblocks.content.memory import MemoryContent, MemoryMetadata
from streamblocks.content.message import MessageContent, MessageMetadata

__all__ = [
    # Base
    "BaseContent",
    # File operations
    "FileOperationsContent",
    "FileOperationsMetadata",
    "FileContentContent",
    "FileContentMetadata",
    # Patch
    "PatchContent",
    "PatchMetadata",
    # Tool calling
    "ToolCallContent",
    "ToolCallMetadata",
    # Visualization
    "VisualizationContent",
    "VisualizationMetadata",
    # Memory
    "MemoryContent",
    "MemoryMetadata",
    # Message
    "MessageContent",
    "MessageMetadata",
    # Interactive base
    "InteractiveMetadata",
    "InteractiveContent",
    # Interactive specific
    "YesNoMetadata",
    "YesNoContent",
    "ChoiceMetadata",
    "ChoiceContent",
    "MultiChoiceMetadata",
    "MultiChoiceContent",
    "InputMetadata",
    "InputContent",
    "ScaleMetadata",
    "ScaleContent",
    "RankingMetadata",
    "RankingContent",
    "ConfirmMetadata",
    "ConfirmContent",
    "FormMetadata",
    "FormContent",
    "FormField",
]
