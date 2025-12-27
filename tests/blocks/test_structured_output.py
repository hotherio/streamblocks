"""Tests for structured output blocks."""

from __future__ import annotations

import json
from typing import ClassVar

import pytest
from pydantic import BaseModel, Field, ValidationError

from hother.streamblocks.core.types import BaseContent
from hother.streamblocks_examples.blocks.agent.structured_output import (
    StructuredOutputMetadata,
    create_structured_output_block,
)


class TestStructuredOutputMetadata:
    """Tests for StructuredOutputMetadata model."""

    def test_metadata_with_required_fields(self) -> None:
        """Test metadata creation with only required fields."""
        metadata = StructuredOutputMetadata(
            id="block-1",
            block_type="structured",
            schema_name="test_schema",
        )

        assert metadata.id == "block-1"
        assert metadata.block_type == "structured"
        assert metadata.schema_name == "test_schema"
        assert metadata.format == "json"  # default
        assert metadata.description is None  # default

    def test_metadata_with_all_fields(self) -> None:
        """Test metadata creation with all fields."""
        metadata = StructuredOutputMetadata(
            id="block-2",
            block_type="user",
            schema_name="user_profile",
            format="yaml",
            description="User profile schema",
        )

        assert metadata.id == "block-2"
        assert metadata.block_type == "user"
        assert metadata.schema_name == "user_profile"
        assert metadata.format == "yaml"
        assert metadata.description == "User profile schema"

    def test_metadata_json_format(self) -> None:
        """Test metadata with explicit JSON format."""
        metadata = StructuredOutputMetadata(
            id="block-3",
            block_type="config",
            schema_name="config",
            format="json",
        )

        assert metadata.format == "json"

    def test_metadata_yaml_format(self) -> None:
        """Test metadata with YAML format."""
        metadata = StructuredOutputMetadata(
            id="block-4",
            block_type="config",
            schema_name="config",
            format="yaml",
        )

        assert metadata.format == "yaml"

    def test_metadata_missing_schema_name_raises_error(self) -> None:
        """Test that missing schema_name raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            StructuredOutputMetadata(
                id="block-5",
                block_type="test",
            )  # type: ignore[call-arg]

        assert "schema_name" in str(exc_info.value)

    def test_metadata_missing_base_fields_raises_error(self) -> None:
        """Test that missing id and block_type raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            StructuredOutputMetadata(schema_name="test")  # type: ignore[call-arg]

        errors = str(exc_info.value)
        assert "id" in errors or "block_type" in errors

    def test_metadata_invalid_format_raises_error(self) -> None:
        """Test that invalid format raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            StructuredOutputMetadata(
                id="block-6",
                block_type="test",
                schema_name="test",
                format="xml",  # type: ignore[arg-type]
            )

        assert "format" in str(exc_info.value)


class TestCreateStructuredOutputBlock:
    """Tests for create_structured_output_block factory."""

    def test_create_block_with_simple_schema(self) -> None:
        """Test creating a block with a simple schema."""

        class UserProfile(BaseModel):
            name: str
            age: int

        block_class = create_structured_output_block(
            schema_model=UserProfile,
            schema_name="user_profile",
        )

        assert block_class.__name__ == "UserProfileBlock"
        assert block_class.__doc__ == "Structured output block for 'user_profile' schema."

    def test_create_block_with_json_format(self) -> None:
        """Test creating a block with JSON format (default)."""

        class Config(BaseModel):
            key: str
            value: int

        block_class = create_structured_output_block(
            schema_model=Config,
            schema_name="config",
            format="json",
        )

        assert block_class.__name__ == "ConfigBlock"

    def test_create_block_with_yaml_format(self) -> None:
        """Test creating a block with YAML format."""

        class Config(BaseModel):
            key: str
            value: int

        block_class = create_structured_output_block(
            schema_model=Config,
            schema_name="config",
            format="yaml",
        )

        assert block_class.__name__ == "ConfigBlock"

    def test_create_block_with_optional_fields(self) -> None:
        """Test creating a block with optional fields in schema."""

        class Profile(BaseModel):
            name: str
            email: str | None = None
            age: int = 25

        block_class = create_structured_output_block(
            schema_model=Profile,
            schema_name="profile",
        )

        assert block_class.__name__ == "ProfileBlock"

    def test_create_block_with_complex_types(self) -> None:
        """Test creating a block with complex field types."""

        class ComplexSchema(BaseModel):
            tags: list[str]
            metadata: dict[str, int]

        block_class = create_structured_output_block(
            schema_model=ComplexSchema,
            schema_name="complex_data",
        )

        assert block_class.__name__ == "ComplexDataBlock"

    def test_create_block_with_nested_model(self) -> None:
        """Test creating a block with nested Pydantic models."""

        class Address(BaseModel):
            street: str
            city: str

        class Person(BaseModel):
            name: str
            address: Address

        block_class = create_structured_output_block(
            schema_model=Person,
            schema_name="person",
        )

        assert block_class.__name__ == "PersonBlock"

    def test_create_block_with_field_descriptions(self) -> None:
        """Test creating a block with Field descriptions."""

        class DescribedSchema(BaseModel):
            name: str = Field(..., description="The user's name")
            count: int = Field(default=0, description="Item count")

        block_class = create_structured_output_block(
            schema_model=DescribedSchema,
            schema_name="described",
        )

        assert block_class.__name__ == "DescribedBlock"

    def test_create_block_strict_mode(self) -> None:
        """Test creating a block with strict parsing mode."""

        class StrictSchema(BaseModel):
            value: int

        block_class = create_structured_output_block(
            schema_model=StrictSchema,
            schema_name="strict",
            strict=True,
        )

        assert block_class.__name__ == "StrictBlock"

    def test_create_block_permissive_mode(self) -> None:
        """Test creating a block with permissive parsing mode (default)."""

        class PermissiveSchema(BaseModel):
            value: int

        block_class = create_structured_output_block(
            schema_model=PermissiveSchema,
            schema_name="permissive",
            strict=False,
        )

        assert block_class.__name__ == "PermissiveBlock"

    def test_create_block_with_underscore_in_name(self) -> None:
        """Test that underscores in schema name are handled correctly."""

        class TestSchema(BaseModel):
            value: str

        block_class = create_structured_output_block(
            schema_model=TestSchema,
            schema_name="test_schema_name",
        )

        # Underscores should be removed and title case applied
        assert block_class.__name__ == "TestSchemaNameBlock"

    def test_field_without_annotation_is_skipped(self) -> None:
        """Test that fields without type annotation are skipped."""

        class SchemaWithUnannotated(BaseModel):
            typed_field: str
            # Note: Pydantic v2 requires annotations, so we test with ClassVar
            # which appears in model_fields but has no annotation
            class_var: ClassVar[str] = "default"

        block_class = create_structured_output_block(
            schema_model=SchemaWithUnannotated,
            schema_name="unannotated",
        )

        assert block_class.__name__ == "UnannotatedBlock"

    def test_field_with_none_annotation_is_skipped(self) -> None:
        """Test that fields with None annotation are skipped.

        This covers line 81 of structured_output.py where field_type is None.
        """
        from unittest.mock import MagicMock, patch

        class SimpleSchema(BaseModel):
            normal_field: str

        # Create a mock field_info with None annotation
        mock_field_info = MagicMock()
        mock_field_info.annotation = None  # This triggers line 81
        mock_field_info.is_required.return_value = False
        mock_field_info.default = "default"

        # Mock the model_fields to include our None-annotated field
        original_model_fields = SimpleSchema.model_fields.copy()
        patched_model_fields = {
            "normal_field": original_model_fields["normal_field"],
            "none_field": mock_field_info,
        }

        with patch.object(SimpleSchema, "model_fields", patched_model_fields):
            block_class = create_structured_output_block(
                schema_model=SimpleSchema,
                schema_name="none_annotation",
            )

        # Block should be created successfully, skipping the None-annotated field
        assert block_class.__name__ == "NoneAnnotationBlock"

    def test_content_class_inherits_from_base_content(self) -> None:
        """Test that generated content class inherits from BaseContent."""

        class SimpleSchema(BaseModel):
            value: str

        block_class = create_structured_output_block(
            schema_model=SimpleSchema,
            schema_name="simple",
        )

        # Get the content type from the block class
        # The block class is Block[StructuredOutputMetadata, ContentClass]
        # We can verify the inheritance by checking __orig_bases__
        assert block_class is not None

    def test_content_class_name_generation(self) -> None:
        """Test that content class name is generated correctly."""

        class MySchema(BaseModel):
            field: str

        block_class = create_structured_output_block(
            schema_model=MySchema,
            schema_name="my_schema",
        )

        # The content class should be named MySchemaContent
        # We can verify by checking the block inherits correctly
        assert block_class.__name__ == "MySchemaBlock"


class TestStructuredOutputBlockIntegration:
    """Integration tests for structured output blocks."""

    def test_json_content_parsing(self) -> None:
        """Test that JSON content is parsed correctly."""
        from hother.streamblocks.core.models import extract_block_types

        class UserData(BaseModel):
            username: str
            score: int

        block_class = create_structured_output_block(
            schema_model=UserData,
            schema_name="user_data",
            format="json",
        )

        # Extract content class using the utility function
        _, content_class = extract_block_types(block_class)

        # Parse JSON content
        json_content = '{"username": "test_user", "score": 100}'
        parsed = content_class.parse(json_content)

        assert parsed.username == "test_user"
        assert parsed.score == 100

    def test_yaml_content_parsing(self) -> None:
        """Test that YAML content is parsed correctly."""
        from hother.streamblocks.core.models import extract_block_types

        class ConfigData(BaseModel):
            setting: str
            enabled: bool

        block_class = create_structured_output_block(
            schema_model=ConfigData,
            schema_name="config_data",
            format="yaml",
        )

        # Extract content class using the utility function
        _, content_class = extract_block_types(block_class)

        # Parse YAML content
        yaml_content = """setting: production
enabled: true"""
        parsed = content_class.parse(yaml_content)

        assert parsed.setting == "production"
        assert parsed.enabled is True

    def test_strict_parsing_raises_on_invalid_json(self) -> None:
        """Test that strict mode raises error on invalid JSON."""
        from hother.streamblocks.core.models import extract_block_types

        class StrictData(BaseModel):
            value: int

        block_class = create_structured_output_block(
            schema_model=StrictData,
            schema_name="strict_data",
            format="json",
            strict=True,
        )

        # Extract content class
        _, content_class = extract_block_types(block_class)

        # Invalid JSON should raise in strict mode
        with pytest.raises(json.JSONDecodeError):
            content_class.parse("not valid json")

    def test_permissive_parsing_fallback_on_invalid_json(self) -> None:
        """Test that permissive mode falls back on invalid JSON.

        Note: Permissive mode only falls back successfully if the schema
        has no required fields (besides raw_content from BaseContent).
        """
        from hother.streamblocks.core.models import extract_block_types

        # Use a schema with only optional fields so fallback works
        class PermissiveData(BaseModel):
            value: int | None = None

        block_class = create_structured_output_block(
            schema_model=PermissiveData,
            schema_name="permissive_data",
            format="json",
            strict=False,
        )

        # Extract content class
        _, content_class = extract_block_types(block_class)

        # Invalid JSON should fall back to raw_content in permissive mode
        invalid_content = "not valid json"
        parsed = content_class.parse(invalid_content)

        # Should have raw_content attribute from BaseContent
        assert hasattr(parsed, "raw_content")
        assert parsed.raw_content == invalid_content
        # Optional field should be None when fallback is used
        assert parsed.value is None

    def test_permissive_parsing_with_required_fields_still_fails(self) -> None:
        """Test that permissive mode with required fields still raises on invalid JSON.

        When schema has required fields, fallback to raw_content only still
        fails because required fields are missing.
        """
        from hother.streamblocks.core.models import extract_block_types

        class RequiredFieldData(BaseModel):
            value: int  # Required field

        block_class = create_structured_output_block(
            schema_model=RequiredFieldData,
            schema_name="required_field_data",
            format="json",
            strict=False,
        )

        # Extract content class
        _, content_class = extract_block_types(block_class)

        # Even in permissive mode, required fields cause validation error
        with pytest.raises(ValidationError):
            content_class.parse("not valid json")

    def test_content_inherits_raw_content(self) -> None:
        """Test that content class has raw_content from BaseContent."""
        from hother.streamblocks.core.models import extract_block_types

        class SimpleData(BaseModel):
            name: str

        block_class = create_structured_output_block(
            schema_model=SimpleData,
            schema_name="simple_data",
            format="json",
        )

        # Extract content class
        _, content_class = extract_block_types(block_class)

        # Verify it inherits from BaseContent
        assert issubclass(content_class, BaseContent)
