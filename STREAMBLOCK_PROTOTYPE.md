# StreamBlocks: A Streaming Block Extraction Library

## Overview

StreamBlocks is a sophisticated Python library designed to extract structured blocks of data from streaming text sources. Built on top of an async cancellation framework, it provides a robust system for identifying, parsing, and processing structured content blocks in real-time from asynchronous streams.

The library is particularly useful for:
- Processing streaming API responses that contain structured data
- Extracting actionable content from Large Language Model outputs
- Parsing structured logs or command streams
- Real-time document processing with embedded markup

## Core Concepts

### Block Format
Blocks are delimited by special markers in the stream:
- **Start marker**: `!!<hash>:<block_type>[:<additional_info>]`
- **End marker**: `!!<hash>:end`

Example:
```
!!file01:files_operations
src/main.py:C
src/utils.py:C
README.md:E
!!file01:end
```

### Key Features

1. **Stream Processing**: Processes data as it arrives, maintaining state across chunks
2. **Type-Safe**: Full Pydantic models with validation
3. **Pluggable Parsers**: Extensible parser system for custom block types
4. **Cancellable Operations**: Integration with async cancellation framework
5. **Progress Tracking**: Real-time progress reporting and monitoring
6. **Error Handling**: Robust error handling with detailed logging

## Architecture

### Core Components

1. **BlockExtractor** (`extraction.py`): Main extraction engine that processes lines and identifies blocks
2. **BlockParser** (`parsers/base.py`): Abstract base class for block type parsers
3. **BlockRegistry** (`registry.py`): Registry system for managing available parsers
4. **Models** (`models.py`): Pydantic models for type-safe data handling

### Data Models

```python
class ExtractedBlock:
    hash_id: str              # Unique block identifier
    block_type: str           # Type of the block
    parameters: Dict[str, Any] # Parsed parameters from header
    content: Any              # Parsed content (type depends on parser)
    raw_content: str          # Original unparsed content

class BlockExtractionState:
    line_buffer: str          # Buffer for incomplete lines
    current_block_hash: str   # Current block being processed
    extracted_blocks: List    # All extracted blocks
    processed_lines: int      # Statistics
    discarded_lines: int      # Non-block content
```

## Built-in Block Types

### 1. Simple Blocks
Basic text content blocks without complex parsing.
```
!!simple01:simple
This is simple text content
that spans multiple lines
!!simple01:end
```

### 2. Complex Blocks
Blocks with sections separated by markers.
```
!!complex01:complex(param1, param2)
--- Section 1 ---
Content for section 1
--- Section 2 ---
Content for section 2
!!complex01:end
```

### 3. File Operations
Tracks file creation, editing, and deletion.
```
!!file01:files_operations
src/main.py:C          # Create
src/utils.py:C         # Create
README.md:E            # Edit
old_file.py:D          # Delete
!!file01:end
```

### 4. Action Blocks
Actions with dependencies and parameters.
```
!!actn01:a:build:after(file01, inst01)
<output_dir>dist/</output_dir>
<config>production.json</config>
<parallel>true</parallel>
!!actn01:end
```

### 5. File Patch Blocks
Unified diff format patches.
```
!!patch01:f:main.py
@@ -10,3 +10,5 @@
 def main():
     print("Hello")
+    print("World")
+    return 0
!!patch01:end
```

### 6. Hierarchy Blocks
Directory/tree structures.
```
!!hier01:hierarchy
project/
├── src/
│   ├── main.py
│   └── utils/
│       └── helpers.py
├── tests/
└── README.md
!!hier01:end
```

### 7. Instruction Blocks
Categorized instructions or commands.
```
!!inst01:instruction(setup, test, deploy)
Setup: Install dependencies with pip
Test: Run pytest with coverage
Deploy: Build and push Docker image
!!inst01:end
```

## Usage Examples

### Basic Stream Processing

```python
from forge.utils.async_utils.streaming.blocks import (
    BlockRegistry,
    process_stream_with_blocks
)

async def process_llm_stream(stream):
    """Process an LLM stream and extract blocks."""
    registry = BlockRegistry.create_default()

    async for event in process_stream_with_blocks(
        stream,
        block_registry=registry,
        debug=True
    ):
        # Access the original event
        if event.original_event:
            print(event.original_event, end="", flush=True)

        # Check if a block was extracted
        if event.metadata.extraction_event_type == "block_extracted":
            block = event.metadata.extracted_block
            print(f"\nExtracted {block.block_type} block!")

            # Process based on block type
            if block.block_type == "files_operations":
                handle_file_operations(block)
            elif block.block_type == "a":  # action
                queue_action(block)
```

### Custom Parser Implementation

```python
from forge.utils.async_utils.streaming.blocks import BlockParser
from pydantic import BaseModel

class CustomContent(BaseModel):
    """Content model for custom blocks."""
    items: List[str]
    metadata: Dict[str, Any]

class CustomParser(BlockParser):
    """Parser for custom block type."""

    block_type: str = "custom"
    description: str = "Custom data blocks"

    def parse_preamble(self, header: str) -> Dict[str, Any]:
        """Parse header after block type."""
        # Extract parameters from header
        params = {}
        if ":" in header:
            params["subtype"] = header.split(":", 1)[1]
        return {"type": "custom", "parameters": params}

    def parse_content(self, content: str) -> CustomContent:
        """Parse block content."""
        lines = content.strip().split("\n")
        items = []
        metadata = {}

        for line in lines:
            if line.startswith("#"):
                # Metadata line
                key, value = line[1:].split("=", 1)
                metadata[key.strip()] = value.strip()
            else:
                items.append(line)

        return CustomContent(items=items, metadata=metadata)

    def validate_block(self, block: ExtractedBlock) -> Optional[str]:
        """Validate the extracted block."""
        if not block.content.items:
            return "Block must contain at least one item"
        return None

# Register custom parser
registry = BlockRegistry.create_default()
registry.register(CustomParser())
```

### Integration with Cancellable Operations

```python
from forge.utils.async_utils import Cancellable

async def process_with_timeout(stream, timeout_seconds=300):
    """Process stream with timeout and cancellation."""

    async with Cancellable.with_timeout(timeout_seconds) as cancel:
        extracted_blocks = []

        async for event in process_stream_with_blocks(
            stream,
            cancellable=cancel
        ):
            if event.metadata.extracted_block:
                block = event.metadata.extracted_block
                extracted_blocks.append(block)

                # Report progress
                await cancel.report_progress(
                    f"Extracted {block.block_type} block",
                    {"total_blocks": len(extracted_blocks)}
                )

        return extracted_blocks
```

## Advanced Features

### 1. Stream State Management
The extractor maintains state across streaming chunks:
- Line buffering for incomplete lines
- Current block tracking
- Statistics (processed lines, discarded content)

### 2. Error Recovery
- Orphaned end tags are ignored
- Mismatched block tags are treated as content
- Parser errors are logged but don't stop processing

### 3. Metadata Tracking
Each processed event includes detailed metadata:
- Event timestamps and sequence numbers
- Extraction state (scanning, in_block, completed)
- Statistics (lines processed, blocks extracted)
- Original event information

### 4. Parser Registry
- Dynamic parser registration
- Default parser set for common block types
- Easy extension with custom parsers

## Performance Considerations

1. **Streaming Efficiency**: Processes data as it arrives without buffering entire stream
2. **Memory Usage**: Only current block is kept in memory
3. **Parser Performance**: Parsers are invoked only when blocks are completed
4. **Regex Optimization**: Compiled patterns for block detection

## Error Handling

The library provides multiple levels of error handling:

1. **Parsing Errors**: Logged but don't stop stream processing
2. **Validation Errors**: Parsers can validate blocks and report issues
3. **Stream Errors**: Propagated to caller
4. **Cancellation**: Clean shutdown with partial results

## API Reference

### Main Functions

#### `process_stream_with_blocks()`
```python
async def process_stream_with_blocks(
    stream: AsyncGenerator[Any, None],
    block_registry: Optional[BlockRegistry] = None,
    cancellable: Optional[Cancellable] = None,
    debug: bool = False
) -> AsyncGenerator[ProcessedEvent[Any, BlockExtractionMetadata], None]
```
Main entry point for processing streams with block extraction.

#### `create_block_extraction_processor()`
```python
def create_block_extraction_processor(
    block_registry: BlockRegistry,
    debug: bool = False
) -> Callable[[Any, int, float], BlockExtractionMetadata]
```
Creates a metadata extractor for use with lower-level stream processing.

### Core Classes

#### `BlockRegistry`
```python
class BlockRegistry:
    def register(self, parser: BlockParser) -> None
    def get_parser(self, block_type: str) -> Optional[BlockParser]
    def list_types(self) -> List[str]
    @classmethod
    def create_default(cls) -> "BlockRegistry"
```

#### `BlockParser` (Abstract Base)
```python
class BlockParser(BaseModel, ABC):
    block_type: str
    description: str

    @abstractmethod
    def parse_preamble(self, header: str) -> Dict[str, Any]

    @abstractmethod
    def parse_content(self, content: str) -> Any

    def format_block(self, block: ExtractedBlock) -> None
    def validate_block(self, block: ExtractedBlock) -> Optional[str]
```

#### `ExtractedBlock`
```python
class ExtractedBlock(BaseModel):
    hash_id: str
    block_type: str
    parameters: Dict[str, Any]
    content: Any
    raw_content: str

    def log_context(self) -> Dict[str, Any]
```

## Integration Example: LLM Response Processing

```python
async def process_llm_response(response_stream):
    """Process structured output from an LLM."""

    registry = BlockRegistry.create_default()
    file_operations = []
    actions = []

    async for event in process_stream_with_blocks(response_stream):
        if event.metadata.extracted_block:
            block = event.metadata.extracted_block

            # Collect operations by type
            if block.block_type == "files_operations":
                file_operations.extend(
                    block.content.all_operations
                )
            elif block.block_type == "a":  # action
                actions.append({
                    "name": block.parameters["action_name"],
                    "deps": block.parameters["dependencies"],
                    "params": block.content.parameters
                })

    # Execute operations in order
    for op_type, path in file_operations:
        if op_type == "create":
            await create_file(path)
        elif op_type == "edit":
            await edit_file(path)
        elif op_type == "delete":
            await delete_file(path)

    # Execute actions respecting dependencies
    await execute_action_dag(actions)
```

## Future Enhancements

Based on the prototype structure, potential enhancements could include:

1. **Block Relationships**: Track dependencies between blocks
2. **Streaming Output**: Emit blocks as soon as they're complete
3. **Block Transformers**: Post-processing pipeline for blocks
4. **Schema Validation**: JSON Schema support for block content
5. **Binary Block Support**: Handle base64-encoded content
6. **Compression**: Support for compressed block content
7. **Parallel Processing**: Process independent blocks concurrently
8. **Block Storage**: Persistent storage backend for extracted blocks
9. **Query Language**: DSL for querying extracted blocks
10. **Visualization**: Tools for visualizing block relationships and dependencies

## Conclusion

StreamBlocks provides a robust foundation for processing structured content from streaming sources, with a focus on extensibility, type safety, and real-time processing capabilities. Its integration with the async cancellation framework ensures reliable operation in production environments, while the pluggable parser system allows for easy customization to domain-specific needs.

The library is particularly well-suited for:
- Building AI agent systems that process structured LLM outputs
- Creating command interpreters for streaming protocols
- Implementing real-time log analysis systems
- Developing streaming data transformation pipelines

With its comprehensive error handling, progress tracking, and cancellation support, StreamBlocks offers a production-ready solution for streaming block extraction challenges.
