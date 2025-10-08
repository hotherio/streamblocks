#!/usr/bin/env python3
"""Example demonstrating structured output blocks with custom Pydantic schemas.

This example shows how to use the create_structured_output_block factory
to create type-safe blocks for any Pydantic model.
"""

import asyncio
from collections.abc import AsyncIterator
from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field

from hother.streamblocks import (
    DelimiterFrontmatterSyntax,
    EventType,
    Registry,
    StreamBlockProcessor,
)
from hother.streamblocks.blocks.structured_output import create_structured_output_block

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
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Basic Person Schema (JSON)")
    print("=" * 70)

    # Create the specialized block type
    PersonBlock = create_structured_output_block(  # noqa: N806
        schema_model=PersonSchema,
        schema_name="person",
        format="json",
        strict=True,  # Strict validation
    )

    # Create syntax and registry
    # The syntax will extract metadata and content classes from the block automatically
    syntax = DelimiterFrontmatterSyntax()
    registry = Registry(syntax=syntax)
    registry.register("person", PersonBlock)

    # Create processor
    processor = StreamBlockProcessor(registry)

    # Example stream with person data
    async def person_stream() -> AsyncIterator[str]:
        text = """Here's a person's profile:

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
"""
        for line in text.split("\n"):
            yield line + "\n"
            await asyncio.sleep(0.001)

    # Process the stream
    async for event in processor.process_stream(person_stream()):
        if event.type == EventType.BLOCK_EXTRACTED:
            block = event.block
            print(f"\n✅ Extracted Person Block: {block.metadata.id}")

            # Type-safe access to structured data
            print(f"   Name: {block.content.name}")
            print(f"   Age: {block.content.age}")
            print(f"   Email: {block.content.email}")
            print(f"   City: {block.content.city}")

            # Can also validate and export as the original schema
            person = PersonSchema(
                name=block.content.name,
                age=block.content.age,
                email=block.content.email,
                city=block.content.city,
            )
            print(f"\n   Validated: {person.model_dump()}")

        elif event.type == EventType.RAW_TEXT:
            if event.data.strip():
                print(f"[TEXT] {event.data.strip()}")


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
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Task List with Validation (JSON)")
    print("=" * 70)

    # Create the task block
    TaskBlock = create_structured_output_block(  # noqa: N806
        schema_model=TaskSchema,
        schema_name="task",
        format="json",
        strict=False,  # Permissive - falls back to raw_content on errors
    )

    # Setup
    syntax = DelimiterFrontmatterSyntax()
    registry = Registry(syntax=syntax)
    registry.register("task", TaskBlock)
    processor = StreamBlockProcessor(registry)

    # Stream with multiple tasks
    async def task_stream() -> AsyncIterator[str]:
        text = """Here are your tasks for today:

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
"""
        for line in text.split("\n"):
            yield line + "\n"
            await asyncio.sleep(0.001)

    # Process
    tasks = []
    async for event in processor.process_stream(task_stream()):
        if event.type == EventType.BLOCK_EXTRACTED:
            block = event.block
            tasks.append(block)

            print(f"\n📋 Task: {block.content.title}")
            print(f"   Priority: {block.content.priority.upper()}")
            print(f"   Due: {block.content.due_date or 'No deadline'}")
            print(f"   Tags: {', '.join(block.content.tags) if block.content.tags else 'None'}")
            if block.content.description:
                print(f"   Description: {block.content.description}")

        elif event.type == EventType.RAW_TEXT:
            if event.data.strip():
                print(f"[TEXT] {event.data.strip()}")

    # Summary
    print(f"\n📊 Total tasks: {len(tasks)}")
    urgent = sum(1 for t in tasks if t.content.priority == Priority.URGENT)
    print(f"   Urgent: {urgent}")
    print(f"   Completed: {sum(1 for t in tasks if t.content.completed)}")


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
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Nested Schema (JSON)")
    print("=" * 70)

    # Create the block
    DetailedPersonBlock = create_structured_output_block(  # noqa: N806
        schema_model=DetailedPersonSchema,
        schema_name="detailed_person",
        format="json",
        strict=True,
    )

    # Setup
    syntax = DelimiterFrontmatterSyntax()
    registry = Registry(syntax=syntax)
    registry.register("detailed_person", DetailedPersonBlock)
    processor = StreamBlockProcessor(registry)

    # Stream
    async def person_stream() -> AsyncIterator[str]:
        text = """Employee profile:

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
"""
        for line in text.split("\n"):
            yield line + "\n"
            await asyncio.sleep(0.001)

    # Process
    async for event in processor.process_stream(person_stream()):
        if event.type == EventType.BLOCK_EXTRACTED:
            block = event.block

            print(f"\n👤 {block.content.name} ({block.content.age} years old)")
            print(f"   Email: {block.content.email}")
            print("\n   📍 Address:")
            print(f"      {block.content.address.street}")
            print(f"      {block.content.address.city}, {block.content.address.state} {block.content.address.zip_code}")

            if block.content.company:
                print(f"\n   🏢 Company: {block.content.company.name}")
                print(f"      Industry: {block.content.company.industry}")
                print(f"      Size: {block.content.company.employee_count} employees")

            if block.content.skills:
                print(f"\n   💻 Skills: {', '.join(block.content.skills)}")


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
    print("\n" + "=" * 70)
    print("EXAMPLE 4: YAML Format")
    print("=" * 70)

    # Create the block with YAML parsing
    ConfigBlock = create_structured_output_block(  # noqa: N806
        schema_model=ConfigSchema,
        schema_name="config",
        format="yaml",  # Using YAML!
        strict=True,
    )

    # Setup
    syntax = DelimiterFrontmatterSyntax()
    registry = Registry(syntax=syntax)
    registry.register("config", ConfigBlock)
    processor = StreamBlockProcessor(registry)

    # Stream with YAML content
    async def config_stream() -> AsyncIterator[str]:
        text = """Application configuration:

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
"""
        for line in text.split("\n"):
            yield line + "\n"
            await asyncio.sleep(0.001)

    # Process
    async for event in processor.process_stream(config_stream()):
        if event.type == EventType.BLOCK_EXTRACTED:
            block = event.block

            print(f"\n⚙️  Application: {block.content.app_name} v{block.content.version}")
            print(f"   Debug mode: {'ON' if block.content.debug else 'OFF'}")

            print("\n   Features:")
            for feature, enabled in block.content.features.items():
                status = "✓" if enabled else "✗"
                print(f"      {status} {feature}")

            print("\n   Allowed hosts:")
            for host in block.content.allowed_hosts:
                print(f"      - {host}")

        elif event.type == EventType.RAW_TEXT:
            if event.data.strip():
                print(f"[TEXT] {event.data.strip()}")


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
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Simulated LLM Structured Output")
    print("=" * 70)

    # Create the block
    AnalysisBlock = create_structured_output_block(  # noqa: N806
        schema_model=AnalysisResult,
        schema_name="analysis",
        format="json",
        strict=True,
    )

    # Setup
    syntax = DelimiterFrontmatterSyntax()
    registry = Registry(syntax=syntax)
    registry.register("analysis", AnalysisBlock)
    processor = StreamBlockProcessor(registry)

    # Simulate streaming LLM response
    async def llm_stream() -> AsyncIterator[str]:
        response = """Let me analyze this text for you.

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
"""

        # Simulate character-by-character streaming (like a real LLM)
        chunk_size = 50
        for i in range(0, len(response), chunk_size):
            chunk = response[i : i + chunk_size]
            yield chunk
            await asyncio.sleep(0.05)  # Simulate network delay

    # Process with real-time feedback
    print("\n[Streaming LLM response...]")

    async for event in processor.process_stream(llm_stream()):
        if event.type == EventType.RAW_TEXT:
            # Stream text as it arrives
            if event.data.strip():
                print(f"{event.data.strip()}")

        elif event.type == EventType.BLOCK_DELTA:
            # Show progress while block is being accumulated
            print(".", end="", flush=True)

        elif event.type == EventType.BLOCK_EXTRACTED:
            block = event.block
            print("\n")

            # Type-safe structured data from LLM!
            print("\n📊 Analysis Results:")
            print(f"   Summary: {block.content.summary}")
            print(f"   Sentiment: {block.content.sentiment.upper()}")
            print(f"   Confidence: {block.content.confidence * 100:.1f}%")

            print("\n   Key Points:")
            for i, point in enumerate(block.content.key_points, 1):
                print(f"      {i}. {point}")

            print("\n   Entities:")
            for entity_type, values in block.content.entities.items():
                print(f"      {entity_type.title()}: {', '.join(values)}")


# ============================================================================
# Main
# ============================================================================


async def main() -> None:
    """Run all examples."""
    print("🎯 Structured Output Blocks Examples")
    print("Demonstrating type-safe blocks with custom Pydantic schemas")

    await example_1_basic_person()
    await example_2_task_list()
    await example_3_nested_schema()
    await example_4_yaml_format()
    await example_5_llm_simulation()

    print("\n" + "=" * 70)
    print("✅ All examples completed!")
    print("\nKey Takeaways:")
    print("  - Use create_structured_output_block() with any Pydantic model")
    print("  - Get type-safe access to structured data from streams")
    print("  - Support both JSON and YAML formats")
    print("  - Perfect for LLM structured outputs")
    print("  - Automatic validation with Pydantic")


if __name__ == "__main__":
    asyncio.run(main())
