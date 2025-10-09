"""Structured output blocks with dynamic Pydantic schema support."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, Field, create_model

from hother.streamblocks.core.models import Block
from hother.streamblocks.core.parsing import ParseStrategy, parse_as_json, parse_as_yaml
from hother.streamblocks.core.types import BaseContent, BaseMetadata

if TYPE_CHECKING:
    from collections.abc import Callable


class StructuredOutputMetadata(BaseMetadata):
    """Metadata for structured output blocks."""

    schema_name: str = Field(..., description="Identifier for the schema")
    format: Literal["json", "yaml"] = Field(default="json", description="Parsing format for content")
    description: str | None = Field(default=None, description="Optional description of the schema")


def create_structured_output_block(
    schema_model: type[BaseModel],
    schema_name: str,
    format: Literal["json", "yaml"] = "json",
    *,
    strict: bool = False,
) -> type[Block[StructuredOutputMetadata, BaseContent]]:
    """Create a structured output block with a custom Pydantic schema.

    This factory function creates a specialized Block class that parses content
    according to a user-defined Pydantic model. The content is automatically
    validated and typed according to the schema.

    Args:
        schema_model: Pydantic BaseModel class defining the content structure
        schema_name: Unique identifier for this schema
        format: Content parsing format - "json" or "yaml"
        strict: If True, use strict parsing (raise errors). If False, fall back to raw_content

    Returns:
        A Block subclass typed with StructuredOutputMetadata and a dynamically
        created content class that inherits from both BaseContent and the schema.

    Example:
        >>> from pydantic import BaseModel
        >>> class UserProfile(BaseModel):
        ...     name: str
        ...     age: int
        ...     email: str
        ...
        >>> UserBlock = create_structured_output_block(
        ...     schema_model=UserProfile,
        ...     schema_name="user_profile",
        ...     format="json",
        ...     strict=True
        ... )
        >>> # Register with a syntax and use in stream processing
        >>> # After extraction: block.data.name, block.data.age, etc.
    """
    # Choose parsing strategy
    strategy = ParseStrategy.STRICT if strict else ParseStrategy.PERMISSIVE

    # Get the appropriate decorator
    decorator: Callable[[type[BaseContent]], type[BaseContent]] = (
        parse_as_json(strategy=strategy) if format == "json" else parse_as_yaml(strategy=strategy)
    )

    # Build field definitions from the schema model
    field_definitions: dict[str, Any] = {}

    for field_name, field_info in schema_model.model_fields.items():
        # Get the field annotation (type)
        field_type = field_info.annotation

        # Skip fields without type annotation
        if field_type is None:
            continue

        # Get the default value or use ... for required fields
        field_default = ... if field_info.is_required() else field_info.default

        field_definitions[field_name] = (field_type, field_default)

    # Create the content class dynamically using Pydantic's create_model
    # This class inherits from BaseContent and includes all schema fields
    content_class_name = f"{schema_name.title().replace('_', '')}Content"

    ContentClass: type[BaseContent] = create_model(  # noqa: N806
        content_class_name,
        __base__=BaseContent,
        **field_definitions,
    )

    # Apply the parsing decorator
    ContentClass = decorator(ContentClass)  # noqa: N806

    # Create a Block subclass with the specialized types
    block_class_name = f"{schema_name.title().replace('_', '')}Block"

    # Create the generic Block type with the specialized metadata and content types
    # The type parameters are automatically extracted by extract_block_types()
    return type(
        block_class_name,
        (Block[StructuredOutputMetadata, ContentClass],),
        {
            "__doc__": f"Structured output block for '{schema_name}' schema.",
            "__module__": __name__,
        },
    )
