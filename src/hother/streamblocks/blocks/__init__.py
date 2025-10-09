"""Block definitions and content models for StreamBlocks."""

from hother.streamblocks.blocks.base import BaseContent
from hother.streamblocks.blocks.files import (
    FileContent,
    FileContentContent,
    FileContentMetadata,
    FileOperations,
    FileOperationsContent,
    FileOperationsMetadata,
)
from hother.streamblocks.blocks.interactive import (
    Choice,
    ChoiceContent,
    ChoiceMetadata,
    Confirm,
    ConfirmContent,
    ConfirmMetadata,
    Form,
    FormContent,
    FormField,
    FormMetadata,
    Input,
    InputContent,
    InputMetadata,
    InteractiveContent,
    InteractiveMetadata,
    MultiChoice,
    MultiChoiceContent,
    MultiChoiceMetadata,
    Ranking,
    RankingContent,
    RankingMetadata,
    Scale,
    ScaleContent,
    ScaleMetadata,
    YesNo,
    YesNoContent,
    YesNoMetadata,
)
from hother.streamblocks.blocks.memory import Memory, MemoryContent, MemoryMetadata
from hother.streamblocks.blocks.message import Message, MessageContent, MessageMetadata
from hother.streamblocks.blocks.patch import Patch, PatchContent, PatchMetadata
from hother.streamblocks.blocks.toolcall import ToolCall, ToolCallContent, ToolCallMetadata
from hother.streamblocks.blocks.visualization import Visualization, VisualizationContent, VisualizationMetadata

__all__ = [
    # Base
    "BaseContent",
    # Block classes
    "Choice",
    "ChoiceContent",
    "ChoiceMetadata",
    "Confirm",
    "ConfirmContent",
    "ConfirmMetadata",
    "FileContent",
    "FileContentContent",
    "FileContentMetadata",
    "FileOperations",
    # File operations
    "FileOperationsContent",
    "FileOperationsMetadata",
    "Form",
    "FormContent",
    "FormField",
    "FormMetadata",
    "Input",
    "InputContent",
    "InputMetadata",
    "InteractiveContent",
    # Interactive base
    "InteractiveMetadata",
    # Memory
    "Memory",
    "MemoryContent",
    "MemoryMetadata",
    "Message",
    # Message
    "MessageContent",
    "MessageMetadata",
    "MultiChoice",
    "MultiChoiceContent",
    "MultiChoiceMetadata",
    "Patch",
    # Patch
    "PatchContent",
    "PatchMetadata",
    "Ranking",
    "RankingContent",
    "RankingMetadata",
    "Scale",
    "ScaleContent",
    "ScaleMetadata",
    # Tool calling
    "ToolCall",
    "ToolCallContent",
    "ToolCallMetadata",
    # Visualization
    "Visualization",
    "VisualizationContent",
    "VisualizationMetadata",
    "YesNo",
    "YesNoContent",
    # Interactive specific
    "YesNoMetadata",
]
