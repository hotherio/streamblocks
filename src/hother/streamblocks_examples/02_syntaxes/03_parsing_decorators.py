#!/usr/bin/env python3
"""Example demonstrating content parsing decorators.

This example shows how to use the @parse_as_yaml() and @parse_as_json() decorators
to automatically parse block content into structured Pydantic models with minimal boilerplate.

Key features demonstrated:
- Automatic YAML/JSON parsing with decorators
- STRICT vs PERMISSIVE error handling strategies
- Non-dict value handling
- Type-safe access to parsed content
- Graceful error recovery
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from textwrap import dedent
from typing import Any

from pydantic import Field

from hother.streamblocks import (
    DelimiterFrontmatterSyntax,
    DelimiterPreambleSyntax,
    MarkdownFrontmatterSyntax,
    Registry,
    StreamBlockProcessor,
)
from hother.streamblocks.core.models import Block
from hother.streamblocks.core.parsing import ParseStrategy, parse_as_json, parse_as_yaml
from hother.streamblocks.core.types import BaseContent, BaseMetadata, BlockEndEvent, BlockErrorEvent, TextContentEvent

# ============================================================================
# EXAMPLE 1: Basic YAML Parsing (Permissive Mode)
# ============================================================================


@parse_as_yaml(strategy=ParseStrategy.PERMISSIVE)
class ConfigContent(BaseContent):
    """Configuration content parsed from YAML.

    With PERMISSIVE strategy, malformed YAML falls back to raw_content.
    """

    app_name: str | None = None
    version: str | None = None
    debug: bool | None = None
    port: int | None = None
    features: dict[str, bool] = Field(default_factory=dict)


class ConfigMetadata(BaseMetadata):
    """Metadata for configuration blocks."""

    block_type: str = "config"
    environment: str | None = None


# Create the block type
ConfigBlock = Block[ConfigMetadata, ConfigContent]


async def example_1_basic_yaml_parsing() -> None:
    """Demonstrate basic YAML parsing with permissive error handling."""
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Basic YAML Parsing (Permissive Mode)")
    print("=" * 70)

    # Create syntax and registry
    syntax = DelimiterPreambleSyntax()
    registry = Registry(syntax=syntax)
    registry.register("config", ConfigBlock)

    # Create processor
    processor = StreamBlockProcessor(registry)

    # Example stream with YAML content
    async def config_stream() -> AsyncIterator[str]:
        text = dedent("""
            Application configuration:

            !!config_prod:config
            app_name: MyApp
            version: 1.2.3
            debug: false
            port: 8080
            features:
              auth: true
              logging: true
              metrics: false
            !!end

            That's the production config. Now here's a malformed one:

            !!config_bad:config
            app_name: BrokenApp
            version: [1, 2
            debug: this is not valid YAML {{
            !!end

            Processing complete.
        """)
        for line in text.split("\n"):
            yield line + "\n"
            await asyncio.sleep(0.001)

    # Process the stream
    print("\nProcessing stream with YAML configs...")
    async for event in processor.process_stream(config_stream()):
        if isinstance(event, BlockEndEvent):
            block = event.get_block()
            if block is not None:
                print("\n✅ Extracted Config Block:")
                print(block.model_dump_json(indent=2))

        elif isinstance(event, TextContentEvent):
            if event.content.strip():
                print(f"[TEXT] {event.content.strip()}")


# ============================================================================
# EXAMPLE 2: Strict JSON Parsing
# ============================================================================


@parse_as_json(strategy=ParseStrategy.STRICT)
class APIResponseContent(BaseContent):
    """API response parsed from JSON.

    With STRICT strategy, malformed JSON raises an exception.
    """

    status: int
    message: str
    data: dict[str, Any] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)


class APIMetadata(BaseMetadata):
    """Metadata for API response blocks."""

    block_type: str = "api_response"
    endpoint: str | None = None


# Create the block type
APIBlock = Block[APIMetadata, APIResponseContent]


async def example_2_strict_json_parsing() -> None:
    """Demonstrate strict JSON parsing that raises on errors."""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Strict JSON Parsing")
    print("=" * 70)

    # Create syntax and registry
    syntax = MarkdownFrontmatterSyntax(fence="```", info_string="json")
    registry = Registry(syntax=syntax)
    registry.register("api_response", APIBlock)

    # Create processor
    processor = StreamBlockProcessor(registry)

    # Example stream with JSON API responses
    async def api_stream() -> AsyncIterator[str]:
        text = dedent("""
            API responses from the server:

            ```json
            ---
            id: resp_001
            block_type: api_response
            endpoint: /users/123
            ---
            {
              "status": 200,
              "message": "User retrieved successfully",
              "data": {
                "user_id": 123,
                "username": "alice",
                "email": "alice@example.com"
              }
            }
            ```

            ```json
            ---
            id: resp_002
            block_type: api_response
            endpoint: /posts
            ---
            {
              "status": 201,
              "message": "Post created",
              "data": {
                "post_id": 456,
                "title": "My New Post",
                "created_at": "2024-12-15T10:30:00Z"
              }
            }
            ```

            All responses processed.
        """)
        for line in text.split("\n"):
            yield line + "\n"
            await asyncio.sleep(0.001)

    # Process the stream
    print("\nProcessing API responses...")
    async for event in processor.process_stream(api_stream()):
        if isinstance(event, BlockEndEvent):
            block = event.get_block()
            if block is None:
                continue

            # Type narrowing for API blocks
            if isinstance(block.metadata, APIMetadata) and isinstance(block.content, APIResponseContent):
                metadata = block.metadata
                content = block.content

                print(f"\n📡 API Response from {metadata.endpoint}")

                # Type-safe access to JSON data
                status_emoji = "✅" if content.status < 300 else "❌"
                print(f"   {status_emoji} Status: {content.status}")
                print(f"   Message: {content.message}")

                if content.data:
                    print("   Data:")
                    for key, value in content.data.items():
                        print(f"      {key}: {value}")

                if content.errors:
                    print("   Errors:")
                    for error in content.errors:
                        print(f"      ❗ {error}")

        elif isinstance(event, BlockErrorEvent):
            print(f"\n❌ Block Rejected: {event.reason}")

        elif isinstance(event, TextContentEvent):
            if event.content.strip():
                print(f"[TEXT] {event.content.strip()}")


# ============================================================================
# EXAMPLE 3: Non-Dict Value Handling
# ============================================================================


@parse_as_yaml(strategy=ParseStrategy.PERMISSIVE, handle_non_dict=True)
class ScalarWrapperContent(BaseContent):
    """Content that wraps scalar YAML values in {'value': ...}."""

    value: str | int | float | bool | None = None


@parse_as_yaml(strategy=ParseStrategy.PERMISSIVE, handle_non_dict=False)
class ScalarNoWrapContent(BaseContent):
    """Content that doesn't wrap scalar values (will fail on scalars)."""

    message: str | None = None


class ScalarMetadata(BaseMetadata):
    """Metadata for scalar value blocks."""

    block_type: str = "scalar"
    data_type: str | None = None


# Create block types
ScalarWrapperBlock = Block[ScalarMetadata, ScalarWrapperContent]
ScalarNoWrapBlock = Block[ScalarMetadata, ScalarNoWrapContent]


async def example_3_non_dict_handling() -> None:
    """Demonstrate handling of non-dict YAML values."""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Non-Dict Value Handling")
    print("=" * 70)

    # Example 3a: With handle_non_dict=True (wraps scalars)
    print("\n3a) With handle_non_dict=True (wraps in 'value' field):")
    print("-" * 70)

    syntax = DelimiterPreambleSyntax()
    registry = Registry(syntax=syntax)
    registry.register("scalar", ScalarWrapperBlock)

    processor = StreamBlockProcessor(registry)

    async def scalar_stream() -> AsyncIterator[str]:
        text = dedent("""
            Scalar values:

            !!scalar_str:scalar
            Hello World
            !!end

            !!scalar_num:scalar
            42
            !!end

            !!scalar_bool:scalar
            true
            !!end

            Done.
        """)
        for line in text.split("\n"):
            yield line + "\n"
            await asyncio.sleep(0.001)

    async for event in processor.process_stream(scalar_stream()):
        if isinstance(event, BlockEndEvent):
            block = event.get_block()
            if block is not None:
                print("   Extracted Block:")
                print(block.model_dump_json(indent=2))

        elif isinstance(event, TextContentEvent):
            if event.content.strip():
                print(f"[TEXT] {event.content.strip()}")

    # Example 3b: With handle_non_dict=False (scalars fail)
    print("\n3b) With handle_non_dict=False (scalars cause fallback):")
    print("-" * 70)

    registry2 = Registry(syntax=syntax)
    registry2.register("scalar", ScalarNoWrapBlock)

    processor2 = StreamBlockProcessor(registry2)

    async def scalar_stream2() -> AsyncIterator[str]:
        text = dedent("""
            Testing with dict and scalar:

            !!scalar_dict:scalar
            message: This is a dict, it works
            !!end

            !!scalar_fail:scalar
            This is a scalar, will fall back to raw_content
            !!end

            Done.
        """)
        for line in text.split("\n"):
            yield line + "\n"
            await asyncio.sleep(0.001)

    async for event in processor2.process_stream(scalar_stream2()):
        if isinstance(event, BlockEndEvent):
            block = event.get_block()
            if block is not None:
                print("   Extracted Block:")
                print(block.model_dump_json(indent=2))

        elif isinstance(event, TextContentEvent):
            if event.content.strip():
                print(f"[TEXT] {event.content.strip()}")


# ============================================================================
# EXAMPLE 4: Real-World Mixed Stream
# ============================================================================


@parse_as_yaml(strategy=ParseStrategy.PERMISSIVE)
class DatabaseConfigContent(BaseContent):
    """Database configuration from YAML."""

    host: str | None = None
    port: int | None = None
    database: str | None = None
    pool_size: int | None = None


@parse_as_json(strategy=ParseStrategy.PERMISSIVE)
class MetricsContent(BaseContent):
    """Performance metrics from JSON."""

    cpu_usage: float | None = None
    memory_mb: int | None = None
    requests_per_sec: int | None = None
    error_rate: float | None = None


class MixedMetadata(BaseMetadata):
    """Metadata for mixed content blocks."""

    timestamp: str | None = None


# Create block types
DBConfigBlock = Block[MixedMetadata, DatabaseConfigContent]
MetricsBlock = Block[MixedMetadata, MetricsContent]


async def example_4_mixed_stream() -> None:
    """Demonstrate processing multiple content types in one stream."""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Real-World Mixed Stream")
    print("=" * 70)

    # Create syntax and registry with multiple block types
    syntax = DelimiterFrontmatterSyntax()
    registry = Registry(syntax=syntax)
    registry.register("db_config", DBConfigBlock)
    registry.register("metrics", MetricsBlock)

    # Create processor
    processor = StreamBlockProcessor(registry)

    # Stream with multiple block types
    async def mixed_stream() -> AsyncIterator[str]:
        text = dedent("""
            System monitoring report:

            !!start
            ---
            id: db_001
            block_type: db_config
            timestamp: "2024-12-15T10:00:00Z"
            ---
            host: db.example.com
            port: 5432
            database: production
            pool_size: 20
            !!end

            Database configured. Now checking metrics:

            !!start
            ---
            id: metrics_001
            block_type: metrics
            timestamp: "2024-12-15T10:01:00Z"
            ---
            {
              "cpu_usage": 45.2,
              "memory_mb": 2048,
              "requests_per_sec": 1250,
              "error_rate": 0.02
            }
            !!end

            !!start
            ---
            id: metrics_002
            block_type: metrics
            timestamp: "2024-12-15T10:02:00Z"
            ---
            {
              "cpu_usage": 52.8,
              "memory_mb": 2156,
              "requests_per_sec": 1420,
              "error_rate": 0.01
            }
            !!end

            Report complete.
        """)
        for line in text.split("\n"):
            yield line + "\n"
            await asyncio.sleep(0.001)

    # Process with type-aware handling
    print("\nProcessing mixed content stream...")

    db_configs: list[Any] = []
    metrics_samples: list[Any] = []

    async for event in processor.process_stream(mixed_stream()):
        if isinstance(event, BlockEndEvent):
            block = event.get_block()
            if block is None:
                continue

            if block.metadata.block_type == "db_config":
                db_configs.append(block)
                print("\n🗄️  Extracted Database Config:")
                print(block.model_dump_json(indent=2))

            elif block.metadata.block_type == "metrics":
                metrics_samples.append(block)
                print("\n📊 Extracted Metrics:")
                print(block.model_dump_json(indent=2))

        elif isinstance(event, TextContentEvent):
            if event.content.strip():
                print(f"[TEXT] {event.content.strip()}")

    # Summary
    print("\n📈 Summary:")
    print(f"   DB Configs: {len(db_configs)}")
    print(f"   Metric Samples: {len(metrics_samples)}")

    if metrics_samples:
        # Calculate average CPU with type checking
        cpu_values: list[float] = []
        for m in metrics_samples:
            if isinstance(m.content, MetricsContent) and m.content.cpu_usage is not None:
                cpu_values.append(m.content.cpu_usage)

        if cpu_values:
            avg_cpu = sum(cpu_values) / len(cpu_values)
            print(f"   Average CPU: {avg_cpu:.1f}%")


# ============================================================================
# EXAMPLE 5: Error Handling Comparison
# ============================================================================


@parse_as_json(strategy=ParseStrategy.PERMISSIVE)
class PermissiveJSONContent(BaseContent):
    """JSON content with permissive parsing."""

    status: str | None = None
    count: int | None = None


@parse_as_json(strategy=ParseStrategy.STRICT)
class StrictJSONContent(BaseContent):
    """JSON content with strict parsing."""

    status: str | None = None
    count: int | None = None


class ErrorTestMetadata(BaseMetadata):
    """Metadata for error testing blocks."""

    expected: str | None = None


# Create block types
PermissiveBlock = Block[ErrorTestMetadata, PermissiveJSONContent]
StrictBlock = Block[ErrorTestMetadata, StrictJSONContent]


async def example_5_error_handling() -> None:
    """Compare PERMISSIVE vs STRICT error handling."""
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Error Handling Comparison")
    print("=" * 70)

    # Test data with both valid and invalid JSON
    test_stream_text = dedent("""
        Testing error handling:

        !!test_valid:error_test
        {"status": "ok", "count": 5}
        !!end

        !!test_invalid:error_test
        {this is: not valid JSON at all}
        !!end

        !!test_empty:error_test
        !!end

        Done.
    """)

    # 5a: PERMISSIVE strategy
    print("\n5a) PERMISSIVE Strategy (graceful fallback):")
    print("-" * 70)

    syntax = DelimiterPreambleSyntax()
    registry_permissive = Registry(syntax=syntax)
    registry_permissive.register("error_test", PermissiveBlock)

    processor_permissive = StreamBlockProcessor(registry_permissive)

    async def permissive_stream() -> AsyncIterator[str]:
        for line in test_stream_text.split("\n"):
            yield line + "\n"
            await asyncio.sleep(0.001)

    async for event in processor_permissive.process_stream(permissive_stream()):
        if isinstance(event, BlockEndEvent):
            block = event.get_block()
            if block is not None:
                print("   Extracted Block:")
                print(block.model_dump_json(indent=2))

        elif isinstance(event, TextContentEvent):
            if event.content.strip():
                print(f"[TEXT] {event.content.strip()}")

    # 5b: STRICT strategy
    print("\n5b) STRICT Strategy (raises errors):")
    print("-" * 70)

    registry_strict = Registry(syntax=syntax)
    registry_strict.register("error_test", StrictBlock)

    processor_strict = StreamBlockProcessor(registry_strict)

    async def strict_stream() -> AsyncIterator[str]:
        for line in test_stream_text.split("\n"):
            yield line + "\n"
            await asyncio.sleep(0.001)

    async for event in processor_strict.process_stream(strict_stream()):
        if isinstance(event, BlockEndEvent):
            block = event.get_block()
            if block is not None:
                print("   ✅ Extracted Block:")
                print(block.model_dump_json(indent=2))

        elif isinstance(event, BlockErrorEvent):
            # STRICT mode causes parsing failures to reject the block
            print(f"   ❌ Block rejected: {event.reason}")

        elif isinstance(event, TextContentEvent):
            if event.content.strip():
                print(f"[TEXT] {event.content.strip()}")


# ============================================================================
# Main
# ============================================================================


async def main() -> None:
    """Run all examples."""
    # Suppress library logging to stderr (Example 5 demonstrates error handling)
    logging.getLogger("hother.streamblocks").setLevel(logging.CRITICAL)

    print("🎯 Parsing Decorators Examples")
    print("Demonstrating @parse_as_yaml() and @parse_as_json() decorators")

    await example_1_basic_yaml_parsing()
    await example_2_strict_json_parsing()
    await example_3_non_dict_handling()
    await example_4_mixed_stream()
    await example_5_error_handling()

    print("\n" + "=" * 70)
    print("  - Use @parse_as_yaml() for automatic YAML parsing")
    print("  - Use @parse_as_json() for automatic JSON parsing")
    print("  - PERMISSIVE: falls back to raw_content on errors")
    print("  - STRICT: raises exceptions on parsing errors")
    print("  - handle_non_dict: wraps scalar values in {'value': ...}")
    print("  - Works with any syntax (delimiter, markdown, etc.)")


if __name__ == "__main__":
    asyncio.run(main())
