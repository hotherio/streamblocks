We want to design a small library in Python 3.13 called streamblocks. It means defining the specifications (technical and functional), the interfaces, the data models, provide extensive usage examples and give high level implementation details and considerations. It must be as pythonic as possible.
The purpose of this library is to process and extract blocks from a sync or async stream of text.

A block follows a given syntax and the user can provide its own syntax. We will provide two default block syntaxes:
1. !! delimiter with preamble for metadata
2. markdown fence with frontmatter for metadata
3. !! delimiter with frontmatter for metadata

Example of syntax 1:
```
!!file01:files_operations
src/main.py:C
src/utils.py:C
README.md:E
!!end
```

Example of syntax 2:
```
---
id: file01
name: files_operations
---
src/main.py:C
src/utils.py:C
README.md:E
```

Example of syntax 3:
```
!!start
---
id: file01
name: files_operations
---
src/main.py:C
src/utils.py:C
README.md:E
!!end
```

Another example:
Syntax 1:
```
!!patch01:f:main.py
@@ -10,3 +10,5 @@
 def main():
     print("Hello")
+    print("World")
+    return 0
!!end
```

Syntax 2:
```
---
id: patch01
name: f
path: main.py
---
@@ -10,3 +10,5 @@
 def main():
     print("Hello")
+    print("World")
+    return 0
```

Example of syntax 3:
```
!!start
---
id: patch01
name: f
path: main.py
---
@@ -10,3 +10,5 @@
 def main():
     print("Hello")
+    print("World")
+    return 0
!!end
```

There must be a BlockRegistry where the user can registry its blocks and in different syntax.
Registering a new syntax should have a common interface.
For instance, a block always have metadata and content. In the first syntax, the metadata are parsed in the preamble with where the block opens, while with the second syntax, the metadata are not on the same line. Take that into consideration while designing the whole system.

Metadata should ALWAYS be typed. We don't want something like:
```python
class BlockMetadata(BaseModel):
    """Parsed metadata section – contents depend on syntax."""
    model_config = {"extra": "allow"}
```

The intended usage is as follow:
```python
async for event in process_stream_with_blocks(response_stream):
    if event.metadata.extracted_block:
        block = event.metadata.extracted_block

        # Collect operations by type
        if block.block_type == "files_operations":
            # Do something with this block
        elif block.block_type == "action":  # action
            # Do something with this block
    # We still want to access the rest of the events from the underlying stream
```

During the stream, we always want to know about the candidate and the delta inside:
```python
async for event in process_stream_with_blocks(response_stream):
	if event.metadata.partial_block.delta:
		# We can access just the new content (metadata, content) or the candidate
    elif event.metadata.extracted_block:
        block = event.metadata.extracted_block

        # Collect operations by type
        if block.block_type == "files_operations":
            # Do something with this block
        elif block.block_type == "action":  # action
            # Do something with this block
```

Make sure to include similar examples (normal happy flow and access to partial blocks / candidates).

From a technical point of view, everything needs to be async.
The block detection / extraction process must occur only when there is at least a new line. So the unit to trigger the extraction is N lines (5 by default). This means that to trigger a new events, we accumulate internally 5 lines of new content.

- We do **not** support nested blocks.
- We do **not** attempt recovery inside a broken body – once a block is rejected the bytes are dropped and we resync at the next opening marker.

Hard guarantees

1. Every byte appears in **exactly one** event (`BlockDelta` or `BlockExtracted` or `RawText`).
2. `BlockExtracted` is emitted **only after** the closing marker has been observed _and_ the block has passed the registered validator.
3. Malformed blocks emit `BlockRejected` and **never** `BlockExtracted`.
4. The library is **zero-copy** on the hot path – the only allocation is the final Pydantic model.
5. All public entry points are async iterators and are **AG-UI encoder friendly** – they implement `agui.Encoder` protocol.
6. **Performance knobs**
    - `lines_buffer=N` – trade-off between latency and look-ahead.
    - `max_line_length=16_384` – protect against malicious streams, configurable.

We want the design to use and be compatible with AG-UI protocol:
- https://docs.ag-ui.com/sdk/python/core/overview
- https://docs.ag-ui.com/sdk/python/core/types
- https://docs.ag-ui.com/sdk/python/core/events
- https://docs.ag-ui.com/sdk/python/encoder/overview

Heavily discuss malformed blocks, candidates that becomes invalid, error handling.

Performances matters. For instance, we know that if there are no candidates and no opening tags in the current 5 lines, no need to use a sliding windows, we can discard the buffer. Think clearly about these type of optimization and detail very precisely the whole detection and parsing and extraction algorithms, including the corner cases.

Environment requirements:

We use Pydantic v2 over data classes, type hinting from +3.10 (i.e. we prefer | over Union, dict over Dict, etc.). We use uv as package manager. Prefer StrEnum over Enum. Prefer Literal of StrEnum over Literal of Str.

Some points to be discussed - please discuss if they are relevant, useful or just gimmicky:

	- Callback / Event for extracted blocks
	- Processing / Action: what to do for a block? (e.g. concrete execution for a function calling block)
	- The user can add validator on the metadata and content (like Pydantic does for models)


We actually want a mechanism for the user to parse and validate the preamble/metadata and content and get easily a feedback on this. Here is something we have so far to illustrate (feel free to completely change the interface or design):

```python
"""
Parser for file operations blocks.
"""

from typing import Any, Dict, List, Tuple

from pydantic import BaseModel, Field

from forge.utils.logging import get_logger

from .base import BlockParser

logger = get_logger(__name__)


class FileOperationsContent(BaseModel):
    """Parsed content of file operations block."""

    operations: Dict[str, List[str]] = Field(default_factory=lambda: {"create": [], "delete": [], "edit": []}, description="Operations grouped by type")
    all_operations: List[Tuple[str, str]] = Field(default_factory=list, description="Ordered list of (operation, path) tuples")
    total_operations: int = Field(default=0, description="Total number of operations")
    folders: List[str] = Field(default_factory=list, description="Affected folders")
    files: List[str] = Field(default_factory=list, description="Affected files")
    errors: List[str] = Field(default_factory=list, description="Parsing errors")


class FileOperationsParser(BlockParser):
    """Parser for file operations blocks."""

    block_type: str = "files_operations"
    description: str = "File operations with C/D/E format"

    def parse_preamble(self, header: str) -> Dict[str, Any]:
        """Parse files_operations preamble."""
        return {"type": "files_operations", "parameters": {}}

    def parse_content(self, content: str) -> FileOperationsContent:
        """
        Parse files_operations content.
        Format: path:operation where operation is C/D/E
        """
        result = FileOperationsContent()

        for line_num, line in enumerate(content.split("\n"), 1):
            line = line.strip()
            if not line:
                continue

            if ":" not in line:
                result.errors.append(f"Line {line_num}: Invalid format (missing ':'): {line}")
                continue

            # Use rsplit to handle paths with colons
            parts = line.rsplit(":", 1)
            if len(parts) != 2:
                result.errors.append(f"Line {line_num}: Invalid format: {line}")
                continue

            path = parts[0].strip()
            operation = parts[1].strip().upper()

            if operation == "C":
                result.operations["create"].append(path)
                result.all_operations.append(("create", path))
            elif operation == "D":
                result.operations["delete"].append(path)
                result.all_operations.append(("delete", path))
            elif operation == "E":
                result.operations["edit"].append(path)
                result.all_operations.append(("edit", path))
            else:
                result.errors.append(f"Line {line_num}: Unknown operation '{operation}' for {path}")
                continue

        # Extract folder structure from paths
        folders_set = set()
        files_set = set()

        for op_type, path in result.all_operations:
            if op_type != "delete":  # Don't count deleted files
                parts = path.split("/")
                # Build folder paths
                for i in range(1, len(parts)):
                    folder_path = "/".join(parts[:i])
                    if folder_path:
                        folders_set.add(folder_path)
                # Add the file
                files_set.add(path)

        result.folders = sorted(list(folders_set))
        result.files = sorted(list(files_set))
        result.total_operations = len(result.all_operations)

        return result

    def format_block(self, block) -> None:
        """Custom formatting for file operations blocks."""
        print(f"\n{'-' * 30}")
        print(f"📂 FILE OPERATIONS (Block: {block.hash_id})")
        print(f"{'-' * 30}")

        content = block.content
        print(f"Total operations: {content.total_operations}")

        ops = content.operations

        if ops["create"]:
            print(f"\n✅ CREATE ({len(ops['create'])} files):")
            for path in ops["create"][:10]:
                print(f"   + {path}")
            if len(ops["create"]) > 10:
                print(f"   ... and {len(ops['create']) - 10} more")

        if ops["edit"]:
            print(f"\n✏️  EDIT ({len(ops['edit'])} files):")
            for path in ops["edit"][:10]:
                print(f"   ~ {path}")
            if len(ops["edit"]) > 10:
                print(f"   ... and {len(ops['edit']) - 10} more")

        if ops["delete"]:
            print(f"\n❌ DELETE ({len(ops['delete'])} files):")
            for path in ops["delete"][:10]:
                print(f"   - {path}")
            if len(ops["delete"]) > 10:
                print(f"   ... and {len(ops['delete']) - 10} more")

        # Show folder structure
        if content.folders:
            print(f"\n📁 Folders affected ({len(content.folders)}):")
            for folder in content.folders[:10]:
                depth = folder.count("/")
                indent = "  " * depth
                folder_name = folder.split("/")[-1] if "/" in folder else folder
                print(f"   {indent}📁 {folder_name}/")
            if len(content.folders) > 10:
                print(f"   ... and {len(content.folders) - 10} more folders")

        # Show errors if any
        if content.errors:
            print(f"\n⚠️  ERRORS ({len(content.errors)}):")
            for error in content.errors:
                print(f"   ❗ {error}")
```
It sounds like format_block should be something to convert to AG-UI somehow. Not sure.
