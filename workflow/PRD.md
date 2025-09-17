# StreamBlocks Library Design Specification (Revised)

## 1. Overview

**StreamBlocks** is a Python 3.13+ library for real-time extraction and processing of structured blocks from text streams (sync/async). It provides a pluggable architecture for block syntax definitions, type-safe metadata parsing, and AG-UI protocol compatibility.

## 2. Core Architecture

### 2.1 High-Level Components

```python
from typing import Protocol, AsyncIterator, Generic, TypeVar
from pydantic import BaseModel
from enum import StrEnum
from abc import ABC, abstractmethod

# Core type variables
TMetadata = TypeVar('TMetadata', bound=BaseModel)
TContent = TypeVar('TContent', bound=BaseModel)

class EventType(StrEnum):
    """Event types emitted during stream processing."""
    RAW_TEXT = "raw_text"
    BLOCK_DELTA = "block_delta"
    BLOCK_EXTRACTED = "block_extracted"
    BLOCK_REJECTED = "block_rejected"

class StreamEvent(BaseModel, Generic[TMetadata, TContent]):
    """Base event emitted during stream processing."""
    type: EventType
    data: str  # Raw bytes/text
    metadata: dict | None = None

class BlockState(StrEnum):
    """Internal state of block detection."""
    SEARCHING = "searching"
    HEADER_DETECTED = "header_detected"
    ACCUMULATING_METADATA = "accumulating_metadata"
    ACCUMULATING_CONTENT = "accumulating_content"
    CLOSING_DETECTED = "closing_detected"
    REJECTED = "rejected"
    COMPLETED = "completed"
```

### 2.2 Block Definition Protocol

```python
from dataclasses import dataclass
from typing import Pattern
import re

@dataclass
class DetectionResult:
    """Result from syntax detection attempt."""
    is_opening: bool = False
    is_closing: bool = False
    is_metadata_boundary: bool = False
    metadata: dict | None = None  # For inline metadata (e.g., preamble syntax)

@dataclass
class ParseResult(Generic[TMetadata, TContent]):
    """Result from parsing attempt."""
    success: bool
    metadata: TMetadata | None = None
    content: TContent | None = None
    error: str | None = None

class BlockCandidate:
    """Tracks a potential block being accumulated."""

    def __init__(self, syntax: 'BlockSyntax', start_line: int):
        self.syntax = syntax
        self.start_line = start_line
        self.lines: list[str] = []
        self.state = BlockState.HEADER_DETECTED
        self.metadata_lines: list[str] = []
        self.content_lines: list[str] = []
        self.current_section: str = "header"  # "header", "metadata", "content"

    def add_line(self, line: str) -> None:
        self.lines.append(line)

    @property
    def raw_text(self) -> str:
        return "\n".join(self.lines)

    def compute_hash(self) -> str:
        """Compute hash of first 64 chars for ID."""
        import hashlib
        text_slice = self.raw_text[:64]
        return hashlib.sha256(text_slice.encode()).hexdigest()[:8]

class BlockSyntax(Protocol[TMetadata, TContent]):
    """Protocol for defining block syntax parsers."""

    @property
    def name(self) -> str:
        """Unique syntax identifier."""
        ...

    def detect_line(self, line: str, context: BlockCandidate | None = None) -> DetectionResult:
        """
        Detect if line is significant for this syntax.

        Args:
            line: Current line to check
            context: Current candidate if we're inside a block, None if searching

        Returns:
            DetectionResult indicating what was detected
        """
        ...

    def should_accumulate_metadata(self, candidate: BlockCandidate) -> bool:
        """Check if syntax expects more metadata lines."""
        ...

    def parse_block(self, candidate: BlockCandidate) -> ParseResult[TMetadata, TContent]:
        """Parse a complete block candidate."""
        ...

    def validate_block(self, metadata: TMetadata, content: TContent) -> bool:
        """Additional validation after parsing."""
        ...

class Block(BaseModel, Generic[TMetadata, TContent]):
    """Extracted and validated block."""
    syntax_name: str
    metadata: TMetadata
    content: TContent
    raw_text: str
    line_start: int
    line_end: int
    hash_id: str
```

## 3. Built-in Syntax Implementations

### 3.1 Delimiter with Preamble Syntax

```python
class DelimiterPreambleSyntax(BlockSyntax[TMetadata, TContent]):
    """
    Syntax 1: !! delimiter with inline metadata
    Format: !!<id>:<type>[:param1:param2...]
    """

    def __init__(
        self,
        metadata_class: type[TMetadata],
        content_class: type[TContent],
        delimiter: str = "!!"
    ):
        self.metadata_class = metadata_class
        self.content_class = content_class
        self.delimiter = delimiter
        self._opening_pattern = re.compile(
            rf"^{re.escape(delimiter)}(\w+):(\w+)(:.+)?$"
        )
        self._closing_pattern = re.compile(
            rf"^{re.escape(delimiter)}end$"
        )

    @property
    def name(self) -> str:
        return f"delimiter_preamble_{self.delimiter}"

    def detect_line(self, line: str, context: BlockCandidate | None = None) -> DetectionResult:
        """Detect delimiter-based markers."""
        if context is None:
            # Looking for opening
            match = self._opening_pattern.match(line)
            if match:
                block_id, block_type, params = match.groups()
                metadata_dict = {
                    "id": block_id,
                    "block_type": block_type
                }

                if params:
                    param_parts = params[1:].split(":")
                    for i, part in enumerate(param_parts):
                        metadata_dict[f"param_{i}"] = part

                return DetectionResult(
                    is_opening=True,
                    metadata=metadata_dict  # Inline metadata
                )
        else:
            # Check for closing
            if self._closing_pattern.match(line):
                return DetectionResult(is_closing=True)

        return DetectionResult()

    def should_accumulate_metadata(self, candidate: BlockCandidate) -> bool:
        """No separate metadata section for this syntax."""
        return False

    def parse_block(self, candidate: BlockCandidate) -> ParseResult[TMetadata, TContent]:
        """Parse the complete block."""
        # Metadata was already extracted during detection
        detection = self.detect_line(candidate.lines[0], None)

        if not detection.metadata:
            return ParseResult(success=False, error="Missing metadata in preamble")

        try:
            metadata = self.metadata_class(**detection.metadata)
        except Exception as e:
            return ParseResult(success=False, error=f"Invalid metadata: {e}")

        # Parse content (skip first and last lines)
        content_text = "\n".join(candidate.lines[1:-1])

        try:
            # Assuming content_class has a parse method or accepts raw text
            if hasattr(self.content_class, 'parse'):
                content = self.content_class.parse(content_text)
            else:
                content = self.content_class(raw=content_text)
        except Exception as e:
            return ParseResult(success=False, error=f"Invalid content: {e}")

        return ParseResult(success=True, metadata=metadata, content=content)
```

### 3.2 Markdown Fence with Frontmatter

```python
import yaml

class MarkdownFrontmatterSyntax(BlockSyntax[TMetadata, TContent]):
    """
    Syntax 2: Markdown-style with YAML frontmatter
    Format:
    ```[info]
    ---
    key: value
    ---
    content
    ```
    """

    def __init__(
        self,
        metadata_class: type[TMetadata],
        content_class: type[TContent],
        fence: str = "```",
        info_string: str | None = None
    ):
        self.metadata_class = metadata_class
        self.content_class = content_class
        self.fence = fence
        self.info_string = info_string
        self._fence_pattern = self._build_fence_pattern()
        self._frontmatter_pattern = re.compile(r"^---$")

    def _build_fence_pattern(self) -> Pattern[str]:
        pattern_str = rf"^{re.escape(self.fence)}"
        if self.info_string:
            pattern_str += re.escape(self.info_string)
        return re.compile(pattern_str)

    @property
    def name(self) -> str:
        suffix = f"_{self.info_string}" if self.info_string else ""
        return f"markdown_frontmatter{suffix}"

    def detect_line(self, line: str, context: BlockCandidate | None = None) -> DetectionResult:
        """Detect markdown fence markers and frontmatter boundaries."""
        if context is None:
            # Looking for opening fence
            if self._fence_pattern.match(line):
                return DetectionResult(is_opening=True)
        else:
            # Inside a block
            if context.current_section == "header":
                # Check if this is frontmatter start
                if self._frontmatter_pattern.match(line):
                    context.current_section = "metadata"
                    return DetectionResult(is_metadata_boundary=True)
                else:
                    # No frontmatter, move to content
                    context.current_section = "content"
            elif context.current_section == "metadata":
                # Check for metadata end
                if self._frontmatter_pattern.match(line):
                    context.current_section = "content"
                    return DetectionResult(is_metadata_boundary=True)
                else:
                    context.metadata_lines.append(line)
            elif context.current_section == "content":
                # Check for closing fence
                if line.strip() == self.fence:
                    return DetectionResult(is_closing=True)
                else:
                    context.content_lines.append(line)

        return DetectionResult()

    def should_accumulate_metadata(self, candidate: BlockCandidate) -> bool:
        """Check if we're still in metadata section."""
        return candidate.current_section in ["header", "metadata"]

    def parse_block(self, candidate: BlockCandidate) -> ParseResult[TMetadata, TContent]:
        """Parse the complete block."""
        # Parse metadata from accumulated metadata lines
        metadata_dict = {}
        if candidate.metadata_lines:
            yaml_content = "\n".join(candidate.metadata_lines)
            try:
                metadata_dict = yaml.safe_load(yaml_content) or {}
            except Exception as e:
                return ParseResult(success=False, error=f"Invalid YAML: {e}")

        try:
            metadata = self.metadata_class(**metadata_dict)
        except Exception as e:
            return ParseResult(success=False, error=f"Invalid metadata: {e}")

        # Parse content
        content_text = "\n".join(candidate.content_lines)

        try:
            if hasattr(self.content_class, 'parse'):
                content = self.content_class.parse(content_text)
            else:
                content = self.content_class(raw=content_text)
        except Exception as e:
            return ParseResult(success=False, error=f"Invalid content: {e}")

        return ParseResult(success=True, metadata=metadata, content=content)
```

### 3.3 Hybrid Delimiter with Frontmatter

```python
class DelimiterFrontmatterSyntax(BlockSyntax[TMetadata, TContent]):
    """
    Syntax 3: Delimiter markers with YAML frontmatter
    Format:
    !!start
    ---
    key: value
    ---
    content
    !!end
    """

    def __init__(
        self,
        metadata_class: type[TMetadata],
        content_class: type[TContent],
        start_delimiter: str = "!!start",
        end_delimiter: str = "!!end"
    ):
        self.metadata_class = metadata_class
        self.content_class = content_class
        self.start_delimiter = start_delimiter
        self.end_delimiter = end_delimiter
        self._frontmatter_pattern = re.compile(r"^---$")

    @property
    def name(self) -> str:
        return f"delimiter_frontmatter_{self.start_delimiter}"

    def detect_line(self, line: str, context: BlockCandidate | None = None) -> DetectionResult:
        """Detect delimiter markers and frontmatter boundaries."""
        if context is None:
            # Looking for opening
            if line.strip() == self.start_delimiter:
                return DetectionResult(is_opening=True)
        else:
            # Inside a block
            if context.current_section == "header":
                # Should be frontmatter start
                if self._frontmatter_pattern.match(line):
                    context.current_section = "metadata"
                    return DetectionResult(is_metadata_boundary=True)
                else:
                    # Move directly to content if no frontmatter
                    context.current_section = "content"
                    context.content_lines.append(line)
            elif context.current_section == "metadata":
                if self._frontmatter_pattern.match(line):
                    context.current_section = "content"
                    return DetectionResult(is_metadata_boundary=True)
                else:
                    context.metadata_lines.append(line)
            elif context.current_section == "content":
                if line.strip() == self.end_delimiter:
                    return DetectionResult(is_closing=True)
                else:
                    context.content_lines.append(line)

        return DetectionResult()

    def should_accumulate_metadata(self, candidate: BlockCandidate) -> bool:
        """Check if we're still in metadata section."""
        return candidate.current_section in ["header", "metadata"]

    def parse_block(self, candidate: BlockCandidate) -> ParseResult[TMetadata, TContent]:
        """Parse the complete block."""
        # Similar to MarkdownFrontmatterSyntax
        metadata_dict = {}
        if candidate.metadata_lines:
            yaml_content = "\n".join(candidate.metadata_lines)
            try:
                metadata_dict = yaml.safe_load(yaml_content) or {}
            except Exception as e:
                return ParseResult(success=False, error=f"Invalid YAML: {e}")

        try:
            metadata = self.metadata_class(**metadata_dict)
        except Exception as e:
            return ParseResult(success=False, error=f"Invalid metadata: {e}")

        content_text = "\n".join(candidate.content_lines)

        try:
            if hasattr(self.content_class, 'parse'):
                content = self.content_class.parse(content_text)
            else:
                content = self.content_class(raw=content_text)
        except Exception as e:
            return ParseResult(success=False, error=f"Invalid content: {e}")

        return ParseResult(success=True, metadata=metadata, content=content)
```

## 4. Syntax-Agnostic Stream Processor

```python
from collections import deque
from typing import AsyncGenerator

class StreamBlockProcessor:
    """
    Main stream processing engine.
    Completely syntax-agnostic - delegates all syntax-specific logic to BlockSyntax implementations.
    """

    def __init__(
        self,
        registry: 'BlockRegistry',
        lines_buffer: int = 5,
        max_line_length: int = 16_384,
        max_block_size: int = 1_048_576  # 1MB
    ):
        self.registry = registry
        self.lines_buffer = lines_buffer
        self.max_line_length = max_line_length
        self.max_block_size = max_block_size

        # Processing state
        self._buffer = deque(maxlen=lines_buffer)
        self._candidates: list[BlockCandidate] = []
        self._line_counter = 0
        self._accumulated_text = []

    async def process_stream(
        self,
        stream: AsyncIterator[str]
    ) -> AsyncGenerator[StreamEvent, None]:
        """Process stream and yield events."""

        async for chunk in stream:
            # Accumulate chunks until we have complete lines
            self._accumulated_text.append(chunk)

            # Check if we have complete lines
            text = "".join(self._accumulated_text)
            lines = text.split("\n")

            # Keep incomplete line for next iteration
            if not text.endswith("\n"):
                self._accumulated_text = [lines[-1]]
                lines = lines[:-1]
            else:
                self._accumulated_text = []

            # Process complete lines
            for line in lines:
                # Enforce max line length
                if len(line) > self.max_line_length:
                    line = line[:self.max_line_length]

                self._line_counter += 1

                # Process line through detection pipeline
                async for event in self._process_line(line):
                    yield event

        # Flush remaining candidates at stream end
        async for event in self._flush_candidates():
            yield event

    async def _process_line(
        self,
        line: str
    ) -> AsyncGenerator[StreamEvent, None]:
        """Process a single line through detection."""

        # Add to buffer
        self._buffer.append(line)

        # First, check active candidates
        handled_by_candidate = False

        for candidate in list(self._candidates):
            # Let the syntax check this line in context
            detection = candidate.syntax.detect_line(line, candidate)

            if detection.is_closing:
                # Found closing marker
                candidate.add_line(line)
                candidate.state = BlockState.CLOSING_DETECTED

                # Try to extract block
                event = await self._try_extract_block(candidate)
                if event:
                    yield event
                    self._candidates.remove(candidate)
                    handled_by_candidate = True
                else:
                    # Validation failed, reject
                    yield self._create_rejection_event(candidate)
                    self._candidates.remove(candidate)
                    handled_by_candidate = True

            elif detection.is_metadata_boundary:
                # Syntax detected a metadata boundary
                candidate.add_line(line)
                # Syntax already updated candidate.current_section internally

                # Emit delta event
                yield StreamEvent(
                    type=EventType.BLOCK_DELTA,
                    data=line,
                    metadata={
                        "syntax": candidate.syntax.name,
                        "start_line": candidate.start_line,
                        "current_line": self._line_counter,
                        "section": candidate.current_section,
                        "partial_block": {
                            "delta": line,
                            "accumulated": candidate.raw_text
                        }
                    }
                )
                handled_by_candidate = True

            else:
                # Regular line inside block
                candidate.add_line(line)

                # Check size limit
                if len(candidate.raw_text) > self.max_block_size:
                    yield self._create_rejection_event(
                        candidate,
                        reason="Block size exceeded"
                    )
                    self._candidates.remove(candidate)
                    handled_by_candidate = True
                    continue

                # The syntax's detect_line may have updated internal state
                # (e.g., added to metadata_lines or content_lines)

                # Emit delta event
                yield StreamEvent(
                    type=EventType.BLOCK_DELTA,
                    data=line,
                    metadata={
                        "syntax": candidate.syntax.name,
                        "start_line": candidate.start_line,
                        "current_line": self._line_counter,
                        "section": candidate.current_section,
                        "partial_block": {
                            "delta": line,
                            "accumulated": candidate.raw_text
                        }
                    }
                )
                handled_by_candidate = True

        # If not handled by any candidate, check for new block openings
        if not handled_by_candidate:
            opening_found = False

            for syntax in self.registry.get_syntaxes():
                detection = syntax.detect_line(line, None)

                if detection.is_opening:
                    # Start new candidate
                    candidate = BlockCandidate(syntax, self._line_counter)
                    candidate.add_line(line)

                    # If syntax provided inline metadata, store it
                    if detection.metadata:
                        # This is for syntaxes like DelimiterPreamble
                        # that extract metadata from the opening line
                        candidate.metadata_lines = [str(detection.metadata)]

                    self._candidates.append(candidate)
                    opening_found = True
                    break  # First matching syntax wins

            # If no candidates and no openings, emit raw text
            if not opening_found:
                yield StreamEvent(
                    type=EventType.RAW_TEXT,
                    data=line,
                    metadata={"line_number": self._line_counter}
                )

    async def _try_extract_block(
        self,
        candidate: BlockCandidate
    ) -> StreamEvent | None:
        """Try to parse and validate a complete block."""

        # Delegate parsing to the syntax
        parse_result = candidate.syntax.parse_block(candidate)

        if not parse_result.success:
            return None

        metadata = parse_result.metadata
        content = parse_result.content

        # Additional validation from syntax
        if not candidate.syntax.validate_block(metadata, content):
            return None

        # Registry validation (user-defined validators)
        block_type = getattr(metadata, 'block_type', None)
        if block_type and not self.registry.validate_block(
            block_type, metadata, content
        ):
            return None

        # Create block
        block = Block(
            syntax_name=candidate.syntax.name,
            metadata=metadata,
            content=content,
            raw_text=candidate.raw_text,
            line_start=candidate.start_line,
            line_end=self._line_counter,
            hash_id=candidate.compute_hash()
        )

        return StreamEvent(
            type=EventType.BLOCK_EXTRACTED,
            data=candidate.raw_text,
            metadata={"extracted_block": block}
        )

    def _create_rejection_event(
        self,
        candidate: BlockCandidate,
        reason: str = "Validation failed"
    ) -> StreamEvent:
        """Create a rejection event."""
        return StreamEvent(
            type=EventType.BLOCK_REJECTED,
            data=candidate.raw_text,
            metadata={
                "reason": reason,
                "syntax": candidate.syntax.name,
                "lines": (candidate.start_line, self._line_counter)
            }
        )

    async def _flush_candidates(self) -> AsyncGenerator[StreamEvent, None]:
        """Flush remaining candidates as rejected."""
        for candidate in self._candidates:
            yield self._create_rejection_event(
                candidate,
                reason="Stream ended without closing marker"
            )
        self._candidates.clear()
```

## 5. Performance Optimizations

```python
class OptimizedStreamProcessor(StreamBlockProcessor):
    """Optimized processor with additional heuristics."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._opening_hints = self._build_opening_hints()

    def _build_opening_hints(self) -> set[str]:
        """Build quick-check hints from registered syntaxes."""
        hints = set()

        for syntax in self.registry.get_syntaxes():
            # Ask each syntax for its opening hints
            if hasattr(syntax, 'get_opening_hints'):
                hints.update(syntax.get_opening_hints())
            else:
                # Fallback: try to extract from the syntax somehow
                # This is implementation-specific
                pass

        return hints

    async def _process_line(
        self,
        line: str
    ) -> AsyncGenerator[StreamEvent, None]:
        """Enhanced processing with optimizations."""

        # Fast path: if no candidates and line doesn't look like opening
        if not self._candidates and not self._could_be_opening(line):
            # Can immediately emit and potentially clear buffer
            yield StreamEvent(
                type=EventType.RAW_TEXT,
                data=line,
                metadata={"line_number": self._line_counter}
            )

            # Clear buffer if we're sure no block is starting
            if len(self._buffer) >= self.lines_buffer:
                self._buffer.clear()
            return

        # Continue with normal processing
        async for event in super()._process_line(line):
            yield event

    def _could_be_opening(self, line: str) -> bool:
        """Quick heuristic check if line could be an opening."""
        # Check against pre-computed hints
        line_start = line[:10].strip() if len(line) >= 10 else line.strip()
        return any(line_start.startswith(hint) for hint in self._opening_hints)

# Syntaxes can provide hints for optimization
class OptimizedDelimiterSyntax(DelimiterPreambleSyntax):
    """Delimiter syntax with optimization hints."""

    def get_opening_hints(self) -> set[str]:
        """Provide hints for quick opening detection."""
        return {self.delimiter}
```

## 6. Block Registry

```python
from typing import TypeAlias, Callable

BlockType: TypeAlias = str

class BlockRegistry:
    """Registry for block syntaxes and parsers."""

    def __init__(self):
        self._syntaxes: dict[str, BlockSyntax] = {}
        self._block_types: dict[BlockType, list[BlockSyntax]] = {}
        self._validators: dict[BlockType, list[Callable]] = {}
        self._priority_order: list[str] = []  # Syntax names in priority order

    def register_syntax(
        self,
        syntax: BlockSyntax,
        block_types: list[BlockType] | None = None,
        priority: int = 100
    ) -> None:
        """
        Register a syntax parser.

        Args:
            syntax: The syntax implementation
            block_types: Block types this syntax can handle
            priority: Lower number = higher priority for detection
        """
        if syntax.name in self._syntaxes:
            raise ValueError(f"Syntax '{syntax.name}' already registered")

        self._syntaxes[syntax.name] = syntax

        # Map block types to syntaxes
        if block_types:
            for bt in block_types:
                if bt not in self._block_types:
                    self._block_types[bt] = []
                self._block_types[bt].append(syntax)

        # Insert in priority order
        self._priority_order.append(syntax.name)
        self._priority_order.sort(key=lambda name: priority)

    def add_validator(
        self,
        block_type: BlockType,
        validator: Callable[[BaseModel, BaseModel], bool]
    ) -> None:
        """Add a validator for a block type."""
        if block_type not in self._validators:
            self._validators[block_type] = []
        self._validators[block_type].append(validator)

    def get_syntaxes(self) -> list[BlockSyntax]:
        """Get all registered syntaxes in priority order."""
        return [self._syntaxes[name] for name in self._priority_order]

    def validate_block(
        self,
        block_type: BlockType,
        metadata: BaseModel,
        content: BaseModel
    ) -> bool:
        """Run all validators for a block type."""
        validators = self._validators.get(block_type, [])
        return all(v(metadata, content) for v in validators)
```

## 7. Content and Metadata Models

```python
# Example of typed content models
class FileOperation(BaseModel):
    """Single file operation."""
    action: Literal["create", "edit", "delete"]
    path: str

class FileOperationsContent(BaseModel):
    """Content model for file operations blocks."""
    operations: list[FileOperation]

    @classmethod
    def parse(cls, raw_text: str) -> 'FileOperationsContent':
        """Parse file operations from raw text."""
        operations = []
        for line in raw_text.strip().split("\n"):
            if not line.strip():
                continue

            if ":" not in line:
                raise ValueError(f"Invalid format: {line}")

            path, action = line.rsplit(":", 1)
            action_map = {"C": "create", "E": "edit", "D": "delete"}

            if action.upper() not in action_map:
                raise ValueError(f"Unknown action: {action}")

            operations.append(FileOperation(
                action=action_map[action.upper()],
                path=path.strip()
            ))

        return cls(operations=operations)

class FileOperationsMetadata(BaseModel):
    """Metadata for file operations blocks."""
    id: str
    block_type: Literal["files_operations"]
    description: str | None = None

# Example for patch blocks
class PatchContent(BaseModel):
    """Content model for patch blocks."""
    diff: str

    @classmethod
    def parse(cls, raw_text: str) -> 'PatchContent':
        """Validate and store patch content."""
        # Basic validation that it looks like a unified diff
        if not raw_text.strip():
            raise ValueError("Empty patch")

        lines = raw_text.strip().split("\n")
        if not any(line.startswith("@@") for line in lines):
            raise ValueError("Invalid patch format: missing @@ markers")

        return cls(diff=raw_text.strip())

class PatchMetadata(BaseModel):
    """Metadata for patch blocks."""
    id: str
    block_type: Literal["patch"]
    file_path: str
    description: str | None = None
```

## 8. Usage Examples

### 8.1 Complete Example with Multiple Syntaxes

```python
import asyncio
from streamblocks import (
    BlockRegistry,
    DelimiterPreambleSyntax,
    MarkdownFrontmatterSyntax,
    DelimiterFrontmatterSyntax,
    StreamBlockProcessor,
    EventType
)

async def main():
    # Setup registry
    registry = BlockRegistry()

    # Register multiple syntaxes for file operations

    # Syntax 1: Delimiter with preamble
    syntax1 = DelimiterPreambleSyntax(
        metadata_class=FileOperationsMetadata,
        content_class=FileOperationsContent
    )
    registry.register_syntax(syntax1, block_types=["files_operations"], priority=1)

    # Syntax 2: Markdown with frontmatter
    syntax2 = MarkdownFrontmatterSyntax(
        metadata_class=FileOperationsMetadata,
        content_class=FileOperationsContent,
        fence="```",
        info_string="files"
    )
    registry.register_syntax(syntax2, block_types=["files_operations"], priority=2)

    # Syntax 3: Delimiter with frontmatter
    syntax3 = DelimiterFrontmatterSyntax(
        metadata_class=FileOperationsMetadata,
        content_class=FileOperationsContent
    )
    registry.register_syntax(syntax3, block_types=["files_operations"], priority=3)

    # Add custom validator
    def validate_no_root_delete(metadata: FileOperationsMetadata, content: FileOperationsContent) -> bool:
        """Don't allow deleting from root."""
        for op in content.operations:
            if op.action == "delete" and op.path.startswith("/"):
                return False
        return True

    registry.add_validator("files_operations", validate_no_root_delete)

    # Create processor
    processor = StreamBlockProcessor(registry, lines_buffer=5)

    # Process a stream with mixed syntaxes
    async def mock_stream():
        text = """
Some introductory text here.

!!file01:files_operations
src/main.py:C
src/utils.py:E
!!end

More text between blocks.

```files
---
id: file02
block_type: files_operations
description: Second set of operations
---
tests/test_main.py:C
tests/test_utils.py:C
```

And finally:

!!start
---
id: file03
block_type: files_operations
---
README.md:E
LICENSE:C
!!end

Done!
        """.strip()

        for line in text.split("\n"):
            yield line + "\n"
            await asyncio.sleep(0.01)

    # Process and handle events
    blocks_extracted = []

    async for event in processor.process_stream(mock_stream()):
        if event.type == EventType.BLOCK_EXTRACTED:
            block = event.metadata["extracted_block"]
            blocks_extracted.append(block)
            print(f"✅ Extracted block: {block.metadata.id} via {block.syntax_name}")
            for op in block.content.operations:
                print(f"   - {op.action}: {op.path}")

        elif event.type == EventType.BLOCK_DELTA:
            delta = event.metadata["partial_block"]["delta"]
            section = event.metadata["section"]
            print(f"📝 Delta in {section}: {delta[:50]}...")

        elif event.type == EventType.BLOCK_REJECTED:
            reason = event.metadata["reason"]
            print(f"❌ Block rejected: {reason}")

        elif event.type == EventType.RAW_TEXT:
            print(f"Text: {event.data.strip()}")

    print(f"\nTotal blocks extracted: {len(blocks_extracted)}")

asyncio.run(main())
```

### 8.2 AG-UI Integration

```python
from agui import Encoder, Event as AGUIEvent
from agui.core import Block as AGUIBlock

class StreamBlocksEncoder(Encoder):
    """AG-UI encoder for stream blocks."""

    def __init__(self, registry: BlockRegistry):
        self.registry = registry
        self.processor = StreamBlockProcessor(registry)

    async def encode(
        self,
        stream: AsyncIterator[str]
    ) -> AsyncIterator[AGUIEvent]:
        """Convert stream events to AG-UI events."""

        async for event in self.processor.process_stream(stream):
            if event.type == EventType.BLOCK_EXTRACTED:
                block = event.metadata["extracted_block"]

                # Convert to AG-UI block
                agui_block = AGUIBlock(
                    type=block.metadata.block_type,
                    data=block.content.model_dump(),
                    metadata={
                        "id": block.hash_id,
                        "syntax": block.syntax_name,
                        "original_id": block.metadata.id
                    }
                )

                yield AGUIEvent(
                    type="block",
                    block=agui_block
                )

            elif event.type == EventType.RAW_TEXT:
                yield AGUIEvent(
                    type="text",
                    text=event.data
                )

            elif event.type == EventType.BLOCK_DELTA:
                # Emit partial block events for real-time UI updates
                yield AGUIEvent(
                    type="partial",
                    data={
                        "syntax": event.metadata["syntax"],
                        "section": event.metadata["section"],
                        "delta": event.metadata["partial_block"]["delta"],
                        "accumulated_size": len(event.metadata["partial_block"]["accumulated"])
                    }
                )

            elif event.type == EventType.BLOCK_REJECTED:
                # Notify UI about rejected blocks
                yield AGUIEvent(
                    type="error",
                    error={
                        "type": "block_rejected",
                        "reason": event.metadata["reason"],
                        "syntax": event.metadata["syntax"]
                    }
                )

# Example usage with AG-UI
async def render_with_agui():
    registry = setup_registry()  # Setup as before
    encoder = StreamBlocksEncoder(registry)

    async for agui_event in encoder.encode(text_stream):
        if agui_event.type == "block":
            # Render block in UI based on type
            block = agui_event.block
            if block.type == "files_operations":
                await ui.render_file_tree(block.data["operations"])
            elif block.type == "patch":
                await ui.render_diff(block.data["diff"])

        elif agui_event.type == "text":
            await ui.append_text(agui_event.text)

        elif agui_event.type == "partial":
            # Show loading indicator with progress
            await ui.update_loading(
                f"Parsing {agui_event.data['syntax']} block... "
                f"{agui_event.data['accumulated_size']} bytes"
            )
```

### 8.3 Custom Block Parser Example

```python
class FunctionCallMetadata(BaseModel):
    """Metadata for function call blocks."""
    id: str
    block_type: Literal["function_call"]
    function_name: str
    timestamp: str | None = None

class FunctionCallContent(BaseModel):
    """Content for function call blocks."""
    arguments: dict

    @classmethod
    def parse(cls, raw_text: str) -> 'FunctionCallContent':
        """Parse JSON arguments."""
        import json
        try:
            arguments = json.loads(raw_text.strip())
            if not isinstance(arguments, dict):
                raise ValueError("Arguments must be a JSON object")
            return cls(arguments=arguments)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")

# Custom syntax for function calls
class FunctionCallSyntax(BlockSyntax[FunctionCallMetadata, FunctionCallContent]):
    """
    Custom syntax for function calls:
    ##FUNC:function_name:call_id
    {"arg1": "value1", "arg2": "value2"}
    ##END
    """

    def __init__(self):
        self.metadata_class = FunctionCallMetadata
        self.content_class = FunctionCallContent
        self._opening_pattern = re.compile(r"^##FUNC:(\w+):(\w+)$")
        self._closing_pattern = re.compile(r"^##END$")

    @property
    def name(self) -> str:
        return "function_call"

    def detect_line(self, line: str, context: BlockCandidate | None = None) -> DetectionResult:
        if context is None:
            match = self._opening_pattern.match(line.strip())
            if match:
                func_name, call_id = match.groups()
                return DetectionResult(
                    is_opening=True,
                    metadata={
                        "id": call_id,
                        "block_type": "function_call",
                        "function_name": func_name
                    }
                )
        else:
            if self._closing_pattern.match(line.strip()):
                return DetectionResult(is_closing=True)

        return DetectionResult()

    def should_accumulate_metadata(self, candidate: BlockCandidate) -> bool:
        return False  # Metadata in opening line

    def parse_block(self, candidate: BlockCandidate) -> ParseResult[FunctionCallMetadata, FunctionCallContent]:
        # Extract metadata from first line
        detection = self.detect_line(candidate.lines[0], None)
        if not detection.metadata:
            return ParseResult(success=False, error="Missing metadata")

        try:
            metadata = self.metadata_class(**detection.metadata)
        except Exception as e:
            return ParseResult(success=False, error=str(e))

        # Parse content (JSON between markers)
        content_text = "\n".join(candidate.lines[1:-1])

        try:
            content = self.content_class.parse(content_text)
        except Exception as e:
            return ParseResult(success=False, error=str(e))

        return ParseResult(success=True, metadata=metadata, content=content)

    def validate_block(self, metadata: FunctionCallMetadata, content: FunctionCallContent) -> bool:
        # Could add function-specific validation here
        return True

# Usage
registry.register_syntax(
    FunctionCallSyntax(),
    block_types=["function_call"],
    priority=1
)
```

## 9. Error Handling and Edge Cases

### 9.1 Comprehensive Error Handling

```python
class ErrorRecoveryStrategy(StrEnum):
    """Strategies for handling errors."""
    STRICT = "strict"      # Reject on any error
    PERMISSIVE = "permissive"  # Try to extract what we can
    SKIP = "skip"         # Skip malformed blocks silently

class RobustStreamProcessor(StreamBlockProcessor):
    """Processor with configurable error recovery."""

    def __init__(
        self,
        registry: BlockRegistry,
        error_strategy: ErrorRecoveryStrategy = ErrorRecoveryStrategy.STRICT,
        **kwargs
    ):
        super().__init__(registry, **kwargs)
        self.error_strategy = error_strategy

    async def _try_extract_block(
        self,
        candidate: BlockCandidate
    ) -> StreamEvent | None:
        """Try to extract with error recovery."""

        if self.error_strategy == ErrorRecoveryStrategy.STRICT:
            return await super()._try_extract_block(candidate)

        elif self.error_strategy == ErrorRecoveryStrategy.PERMISSIVE:
            # Try normal extraction first
            event = await super()._try_extract_block(candidate)
            if event:
                return event

            # Try partial extraction
            parse_result = candidate.syntax.parse_block(candidate)

            # Even if parsing failed, try to salvage metadata
            if parse_result.metadata:
                # Create block with partial data
                block = Block(
                    syntax_name=candidate.syntax.name,
                    metadata=parse_result.metadata,
                    content=parse_result.content or self._empty_content(),
                    raw_text=candidate.raw_text,
                    line_start=candidate.start_line,
                    line_end=self._line_counter,
                    hash_id=candidate.compute_hash()
                )

                return StreamEvent(
                    type=EventType.BLOCK_EXTRACTED,
                    data=candidate.raw_text,
                    metadata={
                        "extracted_block": block,
                        "partial": True,
                        "error": parse_result.error
                    }
                )

            return None

        else:  # SKIP
            # Silently skip malformed blocks
            return None

    def _empty_content(self) -> BaseModel:
        """Create an empty content model."""
        class EmptyContent(BaseModel):
            raw: str = ""
        return EmptyContent()
```

### 9.2 Edge Cases Documentation

```python
"""
Edge Cases and Their Handling:

1. NESTED BLOCKS (Not Supported)
   Input: !!outer:type\n!!inner:type\ncontent\n!!end\n!!end
   Result: 'inner' treated as content of 'outer', second !!end is raw text

2. UNCLOSED BLOCKS
   Input: !!block:type\ncontent\n[EOF]
   Result: BlockRejected event with reason "Stream ended without closing marker"

3. EMPTY BLOCKS
   Input: !!block:type\n!!end
   Result: Valid block with empty content (if content model allows)

4. MALFORMED METADATA
   Input: ```\n---\ninvalid yaml: [\n---\ncontent\n```
   Result: BlockRejected due to YAML parse error

5. BUFFER BOUNDARIES
   - Blocks can span multiple buffer windows
   - Opening detection happens even at buffer boundaries
   - No blocks are lost due to buffering

6. VERY LONG LINES
   Input: "!!block:type\n" + "x" * 1000000 + "\n!!end"
   Result: Line truncated to max_line_length, block may be rejected if content invalid

7. CONFLICTING SYNTAXES
   Input: !!block:type  (matches both DelimiterPreamble and DelimiterFrontmatter)
   Result: First registered syntax (by priority) wins

8. IMMEDIATE CONTRADICTION
   Input: !!block:type\n```\ncontent\n```\n!!end
   Result: ``` treated as content, not as new block start

9. PARTIAL RECOVERY
   Input: !!block:type\n[invalid content]\n!!end
   With PERMISSIVE strategy: Block extracted with metadata only

10. INTERLEAVED STREAMS
    Multiple blocks can be candidates simultaneously
    Each is tracked independently until closed or rejected
"""
```

## 10. Performance Considerations

```python
class PerformanceMonitor:
    """Monitor and report performance metrics."""

    def __init__(self):
        self.metrics = {
            "lines_processed": 0,
            "bytes_processed": 0,
            "blocks_extracted": 0,
            "blocks_rejected": 0,
            "candidates_created": 0,
            "max_concurrent_candidates": 0,
            "processing_time_ms": 0
        }
        self._start_time = None

    def start(self):
        import time
        self._start_time = time.perf_counter()

    def stop(self):
        import time
        if self._start_time:
            self.metrics["processing_time_ms"] = (
                (time.perf_counter() - self._start_time) * 1000
            )

    def report(self) -> dict:
        """Generate performance report."""
        metrics = self.metrics.copy()

        # Calculate derived metrics
        if metrics["lines_processed"] > 0:
            metrics["lines_per_second"] = (
                metrics["lines_processed"] /
                (metrics["processing_time_ms"] / 1000)
            )
            metrics["extraction_rate"] = (
                metrics["blocks_extracted"] /
                metrics["lines_processed"]
            )

        return metrics

class InstrumentedProcessor(StreamBlockProcessor):
    """Processor with performance instrumentation."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.monitor = PerformanceMonitor()

    async def process_stream(
        self,
        stream: AsyncIterator[str]
    ) -> AsyncGenerator[StreamEvent, None]:
        """Process with monitoring."""
        self.monitor.start()

        try:
            async for event in super().process_stream(stream):
                # Update metrics
                if event.type == EventType.BLOCK_EXTRACTED:
                    self.monitor.metrics["blocks_extracted"] += 1
                elif event.type == EventType.BLOCK_REJECTED:
                    self.monitor.metrics["blocks_rejected"] += 1

                self.monitor.metrics["bytes_processed"] += len(event.data)

                yield event
        finally:
            self.monitor.stop()

    async def _process_line(self, line: str) -> AsyncGenerator[StreamEvent, None]:
        """Track line processing."""
        self.monitor.metrics["lines_processed"] += 1
        self.monitor.metrics["max_concurrent_candidates"] = max(
            self.monitor.metrics["max_concurrent_candidates"],
            len(self._candidates)
        )

        async for event in super()._process_line(line):
            yield event
```

## 11. Complete Project Structure

```
streamblocks/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── types.py           # Core types, protocols, events
│   ├── processor.py        # StreamBlockProcessor (syntax-agnostic)
│   ├── registry.py         # BlockRegistry
│   └── models.py           # Block, BlockCandidate, etc.
├── syntaxes/
│   ├── __init__.py
│   ├── base.py            # BlockSyntax protocol, DetectionResult
│   ├── delimiter.py        # DelimiterPreambleSyntax
│   ├── frontmatter.py      # MarkdownFrontmatterSyntax
│   ├── hybrid.py          # DelimiterFrontmatterSyntax
│   └── custom.py          # Example custom syntaxes
├── content/
│   ├── __init__.py
│   ├── base.py            # Base content models
│   ├── files.py           # FileOperationsContent
│   ├── patch.py           # PatchContent
│   └── function.py        # FunctionCallContent
├── encoders/
│   ├── __init__.py
│   └── agui.py            # AG-UI encoder
├── utils/
│   ├── __init__.py
│   ├── validation.py       # Validation utilities
│   ├── performance.py      # Performance monitoring
│   └── errors.py          # Error handling strategies
├── examples/
│   ├── basic_usage.py
│   ├── custom_syntax.py
│   ├── agui_integration.py
│   └── performance_demo.py
└── tests/
    ├── conftest.py
    ├── test_processor.py
    ├── test_syntaxes.py
    ├── test_registry.py
    ├── test_edge_cases.py
    └── test_performance.py
```

This revised design ensures complete separation between the syntax-agnostic processor and syntax-specific implementations. The processor only knows about the protocol/interface, while all syntax-specific logic is encapsulated in the syntax classes themselves.
