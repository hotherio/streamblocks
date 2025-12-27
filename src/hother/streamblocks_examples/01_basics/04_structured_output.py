#!/usr/bin/env python3
"""Example demonstrating structured output blocks with custom Pydantic schemas.

This example shows how to use the create_structured_output_block factory
to create type-safe blocks for any Pydantic model.
"""

import asyncio
from datetime import date
from enum import StrEnum
from textwrap import dedent
from typing import Any

from pydantic import BaseModel, Field

from hother.streamblocks import Registry, StreamBlockProcessor
from hother.streamblocks.core.types import (
    BlockContentDeltaEvent,
    BlockEndEvent,
    BlockHeaderDeltaEvent,
    BlockMetadataDeltaEvent,
    TextContentEvent,
)
from hother.streamblocks_examples.blocks.agent.structured_output import create_structured_output_block
from hother.streamblocks_examples.helpers.simulator import simulated_stream

# ============================================================================
# EXAMPLE 1: Basic Person Schema
# ============================================================================


class PersonSchema(BaseModel):
    """Simple person data schema."""

    name: str
    age: int
    email: str
    city: str


async def example_1_basic_person() -> None:
    """Basic example with a simple person schema."""
    # Create the specialized block type
    PersonBlock = create_structured_output_block(  # noqa: N806
        schema_model=PersonSchema,
        schema_name="person",
        format="json",
        strict=True,  # Strict validation
    )

    # Create syntax and registry
    # The syntax will extract metadata and content classes from the block automatically
    registry = Registry()
    registry.register("person", PersonBlock)

    # Create processor
    processor = StreamBlockProcessor(registry)

    # Example text with person data
    text = dedent("""
        Here's a person's profile:

        !!start
        ---
        id: person_001
        block_type: person
        schema_name: person
        format: json
        description: User profile from registration
        ---
        {
          "name": "Alice Johnson",
          "age": 28,
          "email": "alice@example.com",
          "city": "San Francisco"
        }
        !!end

        That's the profile data.
    """)

    # Process the stream
    async for event in processor.process_stream(simulated_stream(text)):
        if isinstance(event, BlockEndEvent):
            block = event.get_block()
            if block is None:
                continue
            print("\nExtracted Person Block:")
            print(block.model_dump_json(indent=2))

        elif isinstance(event, TextContentEvent):
            if event.content.strip():
                print(f"[TEXT] {event.content.strip()}")


# ============================================================================
# EXAMPLE 2: Task List with Validation
# ============================================================================


class Priority(StrEnum):
    """Task priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskSchema(BaseModel):
    """Task with validation."""

    title: str = Field(..., min_length=1, max_length=100)
    description: str = ""
    priority: Priority = Priority.MEDIUM
    due_date: date | None = None
    completed: bool = False
    tags: list[str] = Field(default_factory=list)


async def example_2_task_list() -> None:
    """Task list example with validation."""
    # Create the task block
    TaskBlock = create_structured_output_block(  # noqa: N806
        schema_model=TaskSchema,
        schema_name="task",
        format="json",
        strict=False,  # Permissive - falls back to raw_content on errors
    )

    # Setup
    registry = Registry()
    registry.register("task", TaskBlock)
    processor = StreamBlockProcessor(registry)

    # Text with multiple tasks
    text = dedent("""
        Here are your tasks for today:

        !!start
        ---
        id: task_001
        block_type: task
        schema_name: task
        ---
        {
          "title": "Fix critical bug in payment system",
          "description": "Users are reporting failed transactions",
          "priority": "urgent",
          "due_date": "2024-12-15",
          "tags": ["bug", "payments", "urgent"]
        }
        !!end

        !!start
        ---
        id: task_002
        block_type: task
        schema_name: task
        ---
        {
          "title": "Update documentation",
          "description": "Add examples for new API endpoints",
          "priority": "low",
          "tags": ["docs", "api"]
        }
        !!end

        !!start
        ---
        id: task_003
        block_type: task
        schema_name: task
        ---
        {
          "title": "Implement dark mode",
          "priority": "medium",
          "due_date": "2024-12-20",
          "completed": false,
          "tags": ["feature", "ui"]
        }
        !!end

        All tasks loaded!
    """)

    # Process
    tasks: list[Any] = []
    async for event in processor.process_stream(simulated_stream(text)):
        if isinstance(event, BlockEndEvent):
            block = event.get_block()
            if block is None:
                continue
            tasks.append(block)
            print("\n📋 Extracted Task:")
            print(block.model_dump_json(indent=2))

        elif isinstance(event, TextContentEvent):
            if event.content.strip():
                print(f"[TEXT] {event.content.strip()}")

    # Summary
    print(f"\n📊 Total tasks: {len(tasks)}")


# ============================================================================
# EXAMPLE 3: Nested Schema
# ============================================================================


class Address(BaseModel):
    """Address schema."""

    street: str
    city: str
    state: str
    zip_code: str
    country: str = "USA"


class Company(BaseModel):
    """Company schema."""

    name: str
    industry: str
    employee_count: int | None = None


class DetailedPersonSchema(BaseModel):
    """Person with nested data."""

    name: str
    age: int
    email: str
    address: Address
    company: Company | None = None
    skills: list[str] = Field(default_factory=list)


async def example_3_nested_schema() -> None:
    """Example with nested Pydantic models."""
    # Create the block
    DetailedPersonBlock = create_structured_output_block(  # noqa: N806
        schema_model=DetailedPersonSchema,
        schema_name="detailed_person",
        format="json",
        strict=True,
    )

    # Setup
    registry = Registry()
    registry.register("detailed_person", DetailedPersonBlock)
    processor = StreamBlockProcessor(registry)

    # Employee profile text
    text = dedent("""
        Employee profile:

        !!start
        ---
        id: emp_001
        block_type: detailed_person
        schema_name: detailed_person
        ---
        {
          "name": "Bob Smith",
          "age": 35,
          "email": "bob@techcorp.com",
          "address": {
            "street": "123 Tech Avenue",
            "city": "Seattle",
            "state": "WA",
            "zip_code": "98101",
            "country": "USA"
          },
          "company": {
            "name": "TechCorp Inc",
            "industry": "Software",
            "employee_count": 500
          },
          "skills": ["Python", "Rust", "Go", "Kubernetes"]
        }
        !!end

        Profile loaded.
    """)

    # Process
    async for event in processor.process_stream(simulated_stream(text)):
        if isinstance(event, BlockEndEvent):
            block = event.get_block()
            if block is None:
                continue
            print("\n👤 Extracted Profile:")
            print(block.model_dump_json(indent=2))


# ============================================================================
# EXAMPLE 4: YAML Format
# ============================================================================


class ConfigSchema(BaseModel):
    """Configuration schema."""

    app_name: str
    version: str
    debug: bool = False
    features: dict[str, bool] = Field(default_factory=dict)
    allowed_hosts: list[str] = Field(default_factory=list)


async def example_4_yaml_format() -> None:
    """Example using YAML format instead of JSON."""

    # Create the block with YAML parsing
    ConfigBlock = create_structured_output_block(  # noqa: N806
        schema_model=ConfigSchema,
        schema_name="config",
        format="yaml",  # Using YAML!
        strict=True,
    )

    # Setup
    registry = Registry()
    registry.register("config", ConfigBlock)
    processor = StreamBlockProcessor(registry)

    # Text with YAML content
    text = dedent("""
        Application configuration:

        !!start
        ---
        id: config_001
        block_type: config
        schema_name: config
        format: yaml
        ---
        app_name: MyAwesomeApp
        version: 2.5.0
        debug: true
        features:
          authentication: true
          dark_mode: true
          api_v2: false
        allowed_hosts:
          - localhost
          - example.com
          - "*.myapp.com"
        !!end

        Configuration loaded successfully.
    """)

    # Process
    async for event in processor.process_stream(simulated_stream(text)):
        if isinstance(event, BlockEndEvent):
            block = event.get_block()
            if block is None:
                continue
            print("\n⚙️  Extracted Configuration:")
            print(block.model_dump_json(indent=2))

        elif isinstance(event, TextContentEvent):
            if event.content.strip():
                print(f"[TEXT] {event.content.strip()}")


# ============================================================================
# EXAMPLE 5: Simulated LLM Structured Output
# ============================================================================


class AnalysisResult(BaseModel):
    """Analysis result from an LLM."""

    summary: str
    sentiment: str  # positive, negative, neutral
    confidence: float = Field(..., ge=0.0, le=1.0)
    key_points: list[str]
    entities: dict[str, list[str]] = Field(default_factory=dict)


async def example_5_llm_simulation() -> None:
    """Simulate LLM generating structured output."""

    # Create the block
    AnalysisBlock = create_structured_output_block(  # noqa: N806
        schema_model=AnalysisResult,
        schema_name="analysis",
        format="json",
        strict=True,
    )

    # Setup
    registry = Registry()
    registry.register("analysis", AnalysisBlock)
    processor = StreamBlockProcessor(registry)

    # Simulate streaming LLM response
    text = dedent("""
        Let me analyze this text for you.

        I'll provide a structured analysis:

        !!start
        ---
        id: analysis_001
        block_type: analysis
        schema_name: analysis
        description: Sentiment analysis of customer feedback
        ---
        {
          "summary": "Overall positive customer feedback with minor concerns about pricing.",
          "sentiment": "positive",
          "confidence": 0.85,
          "key_points": [
            "Customers love the user interface",
            "Performance improvements are well received",
            "Some concerns about subscription costs",
            "Excellent customer support mentioned multiple times"
          ],
          "entities": {
            "products": ["mobile app", "web dashboard", "API"],
            "features": ["dark mode", "real-time sync", "offline mode"],
            "concerns": ["pricing", "storage limits"]
          }
        }
        !!end

        The analysis is complete. The data shows strong positive sentiment overall.
    """)

    # Process with real-time feedback
    print("\n[Streaming LLM response...]")

    async for event in processor.process_stream(simulated_stream(text)):
        if isinstance(event, TextContentEvent):
            # Stream text as it arrives
            if event.content.strip():
                print(f"{event.content.strip()}")

        elif isinstance(event, (BlockHeaderDeltaEvent, BlockMetadataDeltaEvent, BlockContentDeltaEvent)):
            # Show progress while block is being accumulated
            print(".", end="", flush=True)

        elif isinstance(event, BlockEndEvent):
            block = event.get_block()
            if block is None:
                continue
            print("\n")
            print("\n📊 Analysis Results:")
            print(block.model_dump_json(indent=2))


# ============================================================================
# Main
# ============================================================================


async def main() -> None:
    """Run all examples."""
    await example_1_basic_person()
    await example_2_task_list()
    await example_3_nested_schema()
    await example_4_yaml_format()
    await example_5_llm_simulation()


if __name__ == "__main__":
    asyncio.run(main())
