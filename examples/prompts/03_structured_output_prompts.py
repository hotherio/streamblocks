#!/usr/bin/env python3
"""Example demonstrating prompt generation for structured output blocks.

This example shows how to generate LLM instruction prompts for structured
output blocks created with Pydantic models, in both JSON and YAML formats.
"""

from enum import StrEnum

from pydantic import BaseModel, Field

from hother.streamblocks import DelimiterPreambleSyntax, Registry, Syntax
from hother.streamblocks.blocks.structured_output import create_structured_output_block

# ============================================================================
# Define Pydantic Models
# ============================================================================


class UserProfile(BaseModel):
    """Simple user profile schema."""

    name: str = Field(description="User's full name")
    age: int = Field(description="User's age in years")
    email: str = Field(description="User's email address")
    city: str = Field(description="City of residence")


class Priority(StrEnum):
    """Task priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskInfo(BaseModel):
    """Task information with validation."""

    title: str = Field(description="Task title", min_length=1, max_length=100)
    description: str = Field(default="", description="Detailed description")
    priority: Priority = Field(default=Priority.MEDIUM, description="Task priority level")
    completed: bool = Field(default=False, description="Completion status")
    tags: list[str] = Field(default_factory=list, description="Associated tags")


class AnalysisResult(BaseModel):
    """Complex analysis result with nested structures."""

    summary: str = Field(description="Executive summary of the analysis")
    sentiment: str = Field(description="Overall sentiment (positive/negative/neutral)")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0", ge=0.0, le=1.0)
    key_points: list[str] = Field(description="List of key findings")
    entities: dict[str, list[str]] = Field(default_factory=dict, description="Extracted entities grouped by type")


# ============================================================================
# Example 1: Single Block Prompt - JSON Format
# ============================================================================


def example_1_single_json() -> None:
    """Generate prompt for a single structured block in JSON format."""
    print("\n" + "=" * 80)
    print("EXAMPLE 1: Single Block Prompt - UserProfile (JSON)")
    print("=" * 80)

    # Create the structured output block
    UserBlock = create_structured_output_block(
        schema_model=UserProfile,
        schema_name="user_profile",
        format="json",
        strict=True,
    )

    # Add examples to the block
    UserBlock.__examples__ = [
        {
            "metadata": {
                "id": "u1",
                "block_type": "user_profile_block",
                "schema_name": "user_profile",
                "format": "json",
            },
            "content": {
                "name": "Alice Johnson",
                "age": 28,
                "email": "alice@example.com",
                "city": "San Francisco",
            },
        },
        {
            "metadata": {
                "id": "u2",
                "block_type": "user_profile_block",
                "schema_name": "user_profile",
                "format": "json",
                "description": "New user registration",
            },
            "content": {
                "name": "Bob Smith",
                "age": 35,
                "email": "bob.smith@example.com",
                "city": "New York",
            },
        },
    ]

    # Generate prompt for this block type
    prompt = UserBlock.to_prompt(syntax=Syntax.DELIMITER_PREAMBLE)

    print("\n" + prompt)


# ============================================================================
# Example 2: Single Block Prompt - YAML Format
# ============================================================================


def example_2_single_yaml() -> None:
    """Generate prompt for a single structured block in YAML format."""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Single Block Prompt - UserProfile (YAML)")
    print("=" * 80)

    # Create the same model but with YAML parsing
    UserBlockYaml = create_structured_output_block(
        schema_model=UserProfile,
        schema_name="user_profile_yaml",
        format="yaml",
        strict=True,
    )

    # Add examples to the block
    UserBlockYaml.__examples__ = [
        {
            "metadata": {
                "id": "uy1",
                "block_type": "user_profile_yaml_block",
                "schema_name": "user_profile_yaml",
                "format": "yaml",
            },
            "content": {
                "name": "Charlie Davis",
                "age": 42,
                "email": "charlie.davis@example.com",
                "city": "Austin",
            },
        },
        {
            "metadata": {
                "id": "uy2",
                "block_type": "user_profile_yaml_block",
                "schema_name": "user_profile_yaml",
                "format": "yaml",
                "description": "Profile update",
            },
            "content": {
                "name": "Diana Martinez",
                "age": 31,
                "email": "diana.m@example.com",
                "city": "Seattle",
            },
        },
    ]

    # Generate prompt
    prompt = UserBlockYaml.to_prompt(syntax=Syntax.DELIMITER_PREAMBLE)

    print("\n" + prompt)


# ============================================================================
# Example 3: Registry with Multiple Structured Blocks - JSON
# ============================================================================


def example_3_registry_json() -> None:
    """Generate registry prompt with multiple JSON structured blocks."""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Registry Prompt - Multiple JSON Blocks")
    print("=" * 80)

    # Create multiple blocks in JSON format
    UserBlock = create_structured_output_block(
        schema_model=UserProfile,
        schema_name="user_profile",
        format="json",
    )

    # Add examples to UserBlock
    UserBlock.__examples__ = [
        {
            "metadata": {
                "id": "p1",
                "block_type": "user_profile_block",
                "schema_name": "user_profile",
                "format": "json",
            },
            "content": {
                "name": "Emma Wilson",
                "age": 29,
                "email": "emma.w@example.com",
                "city": "Boston",
            },
        },
    ]

    TaskBlock = create_structured_output_block(
        schema_model=TaskInfo,
        schema_name="task",
        format="json",
    )

    # Add examples to TaskBlock
    TaskBlock.__examples__ = [
        {
            "metadata": {
                "id": "t1",
                "block_type": "task_block",
                "schema_name": "task",
                "format": "json",
            },
            "content": {
                "title": "Implement user authentication",
                "description": "Add JWT-based authentication to the API",
                "priority": "high",
                "completed": False,
                "tags": ["backend", "security"],
            },
        },
        {
            "metadata": {
                "id": "t2",
                "block_type": "task_block",
                "schema_name": "task",
                "format": "json",
            },
            "content": {
                "title": "Write unit tests",
                "description": "Achieve 80% code coverage",
                "priority": "medium",
                "completed": True,
                "tags": ["testing", "quality"],
            },
        },
    ]

    AnalysisBlock = create_structured_output_block(
        schema_model=AnalysisResult,
        schema_name="analysis",
        format="json",
    )

    # Add examples to AnalysisBlock
    AnalysisBlock.__examples__ = [
        {
            "metadata": {
                "id": "a1",
                "block_type": "analysis_block",
                "schema_name": "analysis",
                "format": "json",
                "description": "Customer feedback analysis",
            },
            "content": {
                "summary": "Overall positive feedback with minor concerns about performance",
                "sentiment": "positive",
                "confidence": 0.85,
                "key_points": [
                    "Users love the new UI",
                    "Performance issues on mobile",
                    "Great customer support",
                ],
                "entities": {
                    "products": ["Mobile App", "Web Dashboard"],
                    "features": ["UI", "Customer Support"],
                },
            },
        },
    ]

    # Create registry and register all blocks
    syntax = DelimiterPreambleSyntax()
    registry = Registry(syntax=syntax)
    registry.register("user_profile", UserBlock)
    registry.register("task", TaskBlock)
    registry.register("analysis", AnalysisBlock)

    # Generate comprehensive prompt (with examples this time)
    prompt = registry.to_prompt(include_examples=True)

    print("\n" + prompt)


# ============================================================================
# Example 4: Registry with Mixed JSON and YAML Blocks
# ============================================================================


def example_4_registry_mixed() -> None:
    """Generate registry prompt with both JSON and YAML blocks."""
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Registry Prompt - Mixed JSON and YAML Blocks")
    print("=" * 80)

    # Create blocks with different formats
    UserBlockJson = create_structured_output_block(
        schema_model=UserProfile,
        schema_name="user_json",
        format="json",
    )

    # Add examples to UserBlockJson
    UserBlockJson.__examples__ = [
        {
            "metadata": {
                "id": "ju1",
                "block_type": "user_json_block",
                "schema_name": "user_json",
                "format": "json",
            },
            "content": {
                "name": "Frank Chen",
                "age": 26,
                "email": "frank.chen@example.com",
                "city": "Los Angeles",
            },
        },
    ]

    UserBlockYaml = create_structured_output_block(
        schema_model=UserProfile,
        schema_name="user_yaml",
        format="yaml",
    )

    # Add examples to UserBlockYaml
    UserBlockYaml.__examples__ = [
        {
            "metadata": {
                "id": "yu1",
                "block_type": "user_yaml_block",
                "schema_name": "user_yaml",
                "format": "yaml",
            },
            "content": {
                "name": "Grace Lee",
                "age": 33,
                "email": "grace.lee@example.com",
                "city": "Chicago",
            },
        },
    ]

    TaskBlockJson = create_structured_output_block(
        schema_model=TaskInfo,
        schema_name="task_json",
        format="json",
    )

    # Add examples to TaskBlockJson
    TaskBlockJson.__examples__ = [
        {
            "metadata": {
                "id": "jt1",
                "block_type": "task_json_block",
                "schema_name": "task_json",
                "format": "json",
            },
            "content": {
                "title": "Deploy to production",
                "description": "Roll out version 2.0",
                "priority": "urgent",
                "completed": False,
                "tags": ["deployment", "production"],
            },
        },
    ]

    TaskBlockYaml = create_structured_output_block(
        schema_model=TaskInfo,
        schema_name="task_yaml",
        format="yaml",
    )

    # Add examples to TaskBlockYaml
    TaskBlockYaml.__examples__ = [
        {
            "metadata": {
                "id": "yt1",
                "block_type": "task_yaml_block",
                "schema_name": "task_yaml",
                "format": "yaml",
            },
            "content": {
                "title": "Review pull requests",
                "description": "Code review for PR #123 and #124",
                "priority": "medium",
                "completed": False,
                "tags": ["code-review", "team"],
            },
        },
    ]

    # Create registry
    syntax = DelimiterPreambleSyntax()
    registry = Registry(syntax=syntax)
    registry.register("user_json", UserBlockJson)
    registry.register("user_yaml", UserBlockYaml)
    registry.register("task_json", TaskBlockJson)
    registry.register("task_yaml", TaskBlockYaml)

    # Generate prompt (with examples this time)
    prompt = registry.to_prompt(include_examples=True)

    print("\n" + prompt)


# ============================================================================
# Example 5: Comparing JSON vs YAML Format Descriptions
# ============================================================================


def example_5_format_comparison() -> None:
    """Compare how JSON and YAML formats are described in prompts."""
    print("\n" + "=" * 80)
    print("EXAMPLE 5: Format Description Comparison")
    print("=" * 80)

    # Same model, different formats
    TaskBlockJson = create_structured_output_block(
        schema_model=TaskInfo,
        schema_name="task",
        format="json",
    )

    TaskBlockYaml = create_structured_output_block(
        schema_model=TaskInfo,
        schema_name="task",
        format="yaml",
    )

    print("\n" + "-" * 80)
    print("JSON FORMAT:")
    print("-" * 80)
    prompt_json = TaskBlockJson.to_prompt(syntax=Syntax.DELIMITER_PREAMBLE)
    # Extract just the content format section
    lines = prompt_json.split("\n")
    in_format_section = False
    for line in lines:
        if "**Content Format:**" in line:
            in_format_section = True
        elif in_format_section:
            if line.startswith(("**", "##")):
                break
            print(line)

    print("\n" + "-" * 80)
    print("YAML FORMAT:")
    print("-" * 80)
    prompt_yaml = TaskBlockYaml.to_prompt(syntax=Syntax.DELIMITER_PREAMBLE)
    # Extract just the content format section
    lines = prompt_yaml.split("\n")
    in_format_section = False
    for line in lines:
        if "**Content Format:**" in line:
            in_format_section = True
        elif in_format_section:
            if line.startswith(("**", "##")):
                break
            print(line)


# ============================================================================
# Example 6: Complex Nested Model Prompt
# ============================================================================


def example_6_complex_model() -> None:
    """Generate prompt for a complex model with nested structures."""
    print("\n" + "=" * 80)
    print("EXAMPLE 6: Complex Nested Model - AnalysisResult")
    print("=" * 80)

    # Create block for complex model
    AnalysisBlock = create_structured_output_block(
        schema_model=AnalysisResult,
        schema_name="analysis",
        format="json",
    )

    # Add examples showing complex nested structures
    AnalysisBlock.__examples__ = [
        {
            "metadata": {
                "id": "ac1",
                "block_type": "analysis_block",
                "schema_name": "analysis",
                "format": "json",
                "description": "Q4 Product Review Analysis",
            },
            "content": {
                "summary": "Strong positive sentiment across all product categories with specific concerns about mobile app stability",
                "sentiment": "positive",
                "confidence": 0.92,
                "key_points": [
                    "Excellent desktop experience",
                    "Mobile app crashes frequently",
                    "Customer service highly rated",
                    "Pricing considered fair",
                    "Feature requests for dark mode",
                ],
                "entities": {
                    "products": ["Desktop App", "Mobile App", "Web Platform"],
                    "features": ["UI/UX", "Performance", "Customer Support", "Pricing"],
                    "issues": ["Mobile Crashes", "Missing Dark Mode"],
                    "competitors": ["CompetitorA", "CompetitorB"],
                },
            },
        },
        {
            "metadata": {
                "id": "ac2",
                "block_type": "analysis_block",
                "schema_name": "analysis",
                "format": "json",
                "description": "Social Media Sentiment Analysis",
            },
            "content": {
                "summary": "Mixed sentiment with concerns about recent policy changes but excitement for upcoming features",
                "sentiment": "neutral",
                "confidence": 0.78,
                "key_points": [
                    "Users frustrated with new privacy policy",
                    "High anticipation for Q1 feature release",
                    "Community engagement has increased",
                    "Some users threatening to switch platforms",
                ],
                "entities": {
                    "topics": ["Privacy Policy", "Feature Release", "Community"],
                    "emotions": ["Frustration", "Excitement", "Concern"],
                    "platforms": ["Twitter", "Reddit", "Facebook"],
                },
            },
        },
    ]

    # Generate prompt
    prompt = AnalysisBlock.to_prompt(syntax=Syntax.DELIMITER_PREAMBLE)

    print("\n" + prompt)


# ============================================================================
# Main
# ============================================================================


def main() -> None:
    """Run all examples."""
    print("=" * 80)
    print("🎯 STRUCTURED OUTPUT BLOCK PROMPTS")
    print("Demonstrating prompt generation for Pydantic models")
    print("=" * 80)

    example_1_single_json()
    example_2_single_yaml()
    example_3_registry_json()
    example_4_registry_mixed()
    example_5_format_comparison()
    example_6_complex_model()

    print("\n" + "=" * 80)
    print("✅ ALL EXAMPLES COMPLETED")
    print("=" * 80)
    print("\nKey Observations:")
    print("  • JSON blocks show JSON syntax in content format")
    print("  • YAML blocks show YAML syntax in content format")
    print("  • Schema fields are automatically extracted from Pydantic models")
    print("  • Field descriptions from Pydantic are included in prompts")
    print("  • Both formats work seamlessly with the same registry")
    print("\nUsage:")
    print("  • Use these prompts as system messages for LLMs")
    print("  • LLMs will output structured data in the specified format")
    print("  • The blocks will be automatically parsed and validated")


if __name__ == "__main__":
    main()
