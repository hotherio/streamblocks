# StreamBlocks API Changes - Type-Specific Registry Design

## Overview

StreamBlocks has been redesigned to use type-specific registries that hold exactly one syntax instance. This change simplifies the architecture, improves type safety, and makes the mental model clearer.

## Key Changes

### 1. New `Registry[T]` Class

**Before:**
```python
from streamblocks import BlockRegistry

registry = BlockRegistry()
registry.register_syntax(syntax, block_types=["type1", "type2"], priority=1)
```

**After:**
```python
from streamblocks import Registry

registry = Registry(syntax)  # Registry holds exactly one syntax
```

### 2. Type-Safe Registry

The new Registry is generic over the syntax type:

```python
from streamblocks import Registry, DelimiterPreambleSyntax

# Type-specific registry
registry: Registry[DelimiterPreambleSyntax] = Registry(my_syntax)
```

### 3. No More Priorities or Block Type Mappings

- **Removed:** Priority system for syntax ordering
- **Removed:** Block type to syntax mappings
- **Removed:** Multiple syntaxes per registry

### 4. StreamBlockProcessor Changes

The processor now works with a single syntax type:

```python
# Generic processor
processor = StreamBlockProcessor(registry)

# Direct syntax access
syntax = processor.syntax  # No iteration needed
```

## Migration Guide

### Simple Case - Single Syntax

**Before:**
```python
registry = BlockRegistry()
syntax = DelimiterPreambleSyntax(name="my_syntax", ...)
registry.register_syntax(syntax, block_types=["type1"], priority=1)
processor = StreamBlockProcessor(registry)
```

**After:**
```python
syntax = DelimiterPreambleSyntax(name="my_syntax", ...)
registry = Registry(syntax)
processor = StreamBlockProcessor(registry)
```

### Multiple Syntaxes - Now Use Multiple Processors

**Before:**
```python
registry = BlockRegistry()
registry.register_syntax(syntax1, ["type1"], priority=1)
registry.register_syntax(syntax2, ["type2"], priority=2)
processor = StreamBlockProcessor(registry)

# Process mixed stream
async for event in processor.process_stream(mixed_stream):
    ...
```

**After:**
```python
# Each syntax gets its own processor
registry1 = Registry(syntax1)
processor1 = StreamBlockProcessor(registry1)

registry2 = Registry(syntax2)
processor2 = StreamBlockProcessor(registry2)

# Process different streams with different processors
async for event in processor1.process_stream(stream1):
    ...

async for event in processor2.process_stream(stream2):
    ...
```

## Complete Example

```python
import asyncio
from streamblocks import (
    Registry,
    DelimiterPreambleSyntax,
    EventType,
    StreamBlockProcessor,
)
from streamblocks.content import FileOperationsContent, FileOperationsMetadata

async def main():
    # Create syntax
    syntax = DelimiterPreambleSyntax(
        name="files_syntax",
        metadata_class=FileOperationsMetadata,
        content_class=FileOperationsContent,
    )
    
    # Create type-specific registry
    registry = Registry(syntax)
    
    # Add validators
    registry.add_validator("files_operations", my_validator)
    
    # Create processor
    processor = StreamBlockProcessor(registry)
    
    # Process stream
    async for event in processor.process_stream(my_stream()):
        if event.type == EventType.BLOCK_EXTRACTED:
            block = event.metadata["extracted_block"]
            print(f"Extracted: {block.metadata.id}")

asyncio.run(main())
```

## Benefits

1. **Simplicity**: One syntax per processor, no complex routing
2. **Type Safety**: `Registry[DelimiterPreambleSyntax]` ensures type correctness
3. **Performance**: No iteration through multiple syntaxes
4. **Clear Mental Model**: Registry holds one syntax, processor uses it

## Handling Different Use Cases

### Use Case: Different Syntaxes for Different Streams

Create separate processors:

```python
# For file operations
file_syntax = DelimiterPreambleSyntax(...)
file_registry = Registry(file_syntax)
file_processor = StreamBlockProcessor(file_registry)

# For patches
patch_syntax = MarkdownFrontmatterSyntax(...)
patch_registry = Registry(patch_syntax)
patch_processor = StreamBlockProcessor(patch_registry)
```

### Use Case: Dynamic Block Types

If you need to handle different block types dynamically, consider:

1. Using a single syntax with a flexible content model
2. Creating a custom syntax that internally handles different types
3. Processing different streams with appropriate processors

## Backward Compatibility

A temporary alias is provided:
```python
BlockRegistry = Registry  # Will be removed in future versions
```

However, note that the API has changed - `BlockRegistry()` now requires a syntax parameter.

## Summary

The new design enforces a one-to-one relationship between registries and syntaxes, making StreamBlocks simpler, more type-safe, and easier to understand. Each processor handles exactly one syntax type efficiently.