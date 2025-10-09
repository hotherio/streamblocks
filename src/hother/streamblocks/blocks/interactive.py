"""Interactive content models for user interaction blocks."""

from __future__ import annotations

from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field

from hother.streamblocks.core.models import Block
from hother.streamblocks.core.types import BaseContent, BaseMetadata


class InteractiveMetadata(BaseMetadata):
    """Base metadata for all interactive blocks."""

    # id and block_type inherited from BaseMetadata
    required: bool = True


class InteractiveContent(BaseContent):
    """Base content for all interactive blocks."""

    # raw_content inherited from BaseContent
    prompt: str
    response: Any | None = None
    responded_at: str | None = None

    @classmethod
    def parse(cls, raw_text: str) -> InteractiveContent:
        """Parse YAML content directly into model."""
        data: dict[str, Any] = yaml.safe_load(raw_text) or {}
        return cls(raw_content=raw_text, **data)


# Yes/No Block
class YesNoMetadata(InteractiveMetadata):
    """Metadata for yes/no questions."""

    yes_label: str = "Yes"
    no_label: str = "No"


class YesNoContent(InteractiveContent):
    """Content for yes/no questions."""

    response: bool | None = None


# Single Choice Block
class ChoiceMetadata(InteractiveMetadata):
    """Metadata for single choice questions."""

    display_style: Literal["radio", "dropdown", "list"] = "radio"


class ChoiceContent(InteractiveContent):
    """Content for single choice questions."""

    options: list[str]
    response: str | None = None


# Multiple Choice Block
class MultiChoiceMetadata(InteractiveMetadata):
    """Metadata for multiple choice questions."""

    min_selections: int = 0
    max_selections: int | None = None


class MultiChoiceContent(InteractiveContent):
    """Content for multiple choice questions."""

    options: list[str]
    response: list[str] = Field(default_factory=list)


# Text Input Block
class InputMetadata(InteractiveMetadata):
    """Metadata for text input fields."""

    input_type: Literal["text", "number", "email", "url", "password"] = "text"
    min_length: int = 0
    max_length: int | None = None
    pattern: str | None = None  # Regex pattern for validation


class InputContent(InteractiveContent):
    """Content for text input fields."""

    placeholder: str = ""
    default_value: str = ""
    response: str | None = None


# Scale Rating Block
class ScaleMetadata(InteractiveMetadata):
    """Metadata for scale rating questions."""

    min_value: int = 1
    max_value: int = 10
    step: int = 1


class ScaleContent(InteractiveContent):
    """Content for scale rating questions."""

    labels: dict[int, str] = Field(default_factory=dict[int, str])
    response: int | None = None


# Ranking Block
class RankingMetadata(InteractiveMetadata):
    """Metadata for ranking questions."""

    allow_partial: bool = False  # Allow ranking only some items


class RankingContent(InteractiveContent):
    """Content for ranking questions."""

    items: list[str]
    response: list[str] = Field(default_factory=list)


# Confirmation Block
class ConfirmMetadata(InteractiveMetadata):
    """Metadata for confirmation dialogs."""

    confirm_label: str = "Confirm"
    cancel_label: str = "Cancel"
    danger_mode: bool = False  # Show as dangerous action


class ConfirmContent(InteractiveContent):
    """Content for confirmation dialogs."""

    message: str
    response: bool | None = None


# Form Block
class FormMetadata(InteractiveMetadata):
    """Metadata for form blocks."""

    submit_label: str = "Submit"
    cancel_label: str = "Cancel"


class FormField(BaseModel):
    """Single form field definition."""

    name: str
    label: str
    field_type: Literal["text", "number", "email", "yesno", "choice"]
    required: bool = True
    options: list[str] | None = None
    validation: dict[str, Any] = Field(default_factory=dict)


class FormContent(InteractiveContent):
    """Content for form blocks."""

    fields: list[FormField]
    response: dict[str, Any] = Field(default_factory=dict)


# Block classes (aggregated metadata + content)


class YesNo(Block[YesNoMetadata, YesNoContent]):
    """Yes/No question block."""


class Choice(Block[ChoiceMetadata, ChoiceContent]):
    """Single choice question block."""


class MultiChoice(Block[MultiChoiceMetadata, MultiChoiceContent]):
    """Multiple choice question block."""


class Input(Block[InputMetadata, InputContent]):
    """Text input block."""


class Scale(Block[ScaleMetadata, ScaleContent]):
    """Scale rating block."""


class Ranking(Block[RankingMetadata, RankingContent]):
    """Ranking block."""


class Confirm(Block[ConfirmMetadata, ConfirmContent]):
    """Confirmation dialog block."""


class Form(Block[FormMetadata, FormContent]):
    """Form block."""
