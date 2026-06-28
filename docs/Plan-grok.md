# StreamBlocks Codebase Analysis and Improvement Plan

## Architecture Improvements

### 1. **Simplify Processor Complexity** (High Priority)
The `StreamBlockProcessor` class is doing too much. Consider splitting responsibilities:

```python
# Current: One monolithic processor
class StreamBlockProcessor:
    # 700+ lines handling parsing, state management, events, adapters...

# Proposed: Separate concerns
class StreamParser:
    """Handles line-by-line parsing and state transitions"""

class EventEmitter:
    """Manages event generation and emission"""

class StreamBlockProcessor:
    """Orchestrates parsing and event emission"""
    def __init__(self, parser: StreamParser, emitter: EventEmitter):
        self.parser = parser
        self.emitter = emitter
```

### 2. **Use Protocols Over ABCs for Syntax Interface** (Medium Priority)
Replace `BaseSyntax` ABC with a protocol for better flexibility:

```python
# Current: Abstract base class
class BaseSyntax(ABC):
    @abstractmethod
    def detect_line(self, line: str, candidate: BlockCandidate | None) -> DetectionResult:
        ...

# Proposed: Protocol-based design
class SyntaxProtocol(Protocol):
    def detect_line(self, line: str, candidate: BlockCandidate | None) -> DetectionResult: ...
    def should_accumulate_metadata(self, candidate: BlockCandidate) -> bool: ...
    def extract_block_type(self, candidate: BlockCandidate) -> str | None: ...
    def parse_block(self, candidate: BlockCandidate, block_class: type[Any] | None = None) -> ParseResult: ...
    def validate_block(self, block: ExtractedBlock) -> bool: ...
```

### 3. **Implement Strategy Pattern for Content Parsing** (Medium Priority)
Replace the current `parse` method approach with a strategy pattern:

```python
# Current: Each content class implements parse
class PatchContent(BaseContent):
    @classmethod
    def parse(cls, raw_text: str) -> PatchContent:
        # Custom parsing logic...

# Proposed: Strategy pattern
@dataclass
class ParseStrategy:
    parser: Callable[[str], dict[str, Any]]
    validator: Callable[[dict[str, Any]], bool] | None = None

class ContentParser:
    def __init__(self, strategies: dict[type[BaseContent], ParseStrategy]):
        self.strategies = strategies

    def parse(self, content_type: type[T], raw_text: str) -> T:
        strategy = self.strategies[content_type]
        data = strategy.parser(raw_text)
        if strategy.validator and not strategy.validator(data):
            raise ValueError("Validation failed")
        return content_type(**data)
```

## Typing Improvements

### 1. **Standardize TypeVar Naming and Scoping** (High Priority)
Make TypeVar usage consistent and properly scoped:

```python
# Current: Inconsistent naming and global scope
TMetadata = TypeVar("TMetadata", bound=BaseMetadata)
TContent = TypeVar("TContent", bound=BaseContent)

# Proposed: Consistent naming and method-level generics where appropriate
class Block(Generic[TMetadata_co, TContent_co]):
    """Use covariant TypeVars for immutable data"""
    metadata: TMetadata_co
    content: TContent_co

# For mutable operations, use method-level generics
class Registry:
    def register[TMetadata_contra, TContent_contra](
        self,
        name: str,
        block_class: type[Block[TMetadata_contra, TContent_contra]]
    ) -> None: ...
```

### 2. **Replace Discriminated Unions with Enum-Based Dispatch** (Medium Priority)
The current discriminated union approach is complex. Consider enum-based dispatch:

```python
# Current: Complex discriminated union
StreamEvent = Annotated[
    RawTextEvent | TextDeltaEvent | BlockOpenedEvent | ...,
    Field(discriminator="type")
]

# Proposed: Enum-based dispatch
class EventType(StrEnum):
    RAW_TEXT = "raw_text"
    TEXT_DELTA = "text_delta"
    BLOCK_OPENED = "block_opened"
    # ...

@dataclass
class StreamEvent:
    type: EventType
    data: str
    metadata: dict[str, Any]

    def as_raw_text(self) -> RawTextEvent | None:
        return RawTextEvent(**self.metadata) if self.type == EventType.RAW_TEXT else None
```

### 3. **Use PEP 695 Type Aliases** (Low Priority)
Modernize type aliases to use PEP 695 syntax:

```python
# Current: Old-style type aliases
BlockType = str
ValidatorFunc = Callable[[ExtractedBlock[Any, Any]], bool]

# Proposed: PEP 695 type aliases
type BlockType = str
type ValidatorFunc[TMetadata, TContent] = Callable[
    [ExtractedBlock[TMetadata, TContent]], bool
]
```

## Python Pattern Improvements

### 1. **Implement Result Pattern for Error Handling** (High Priority)
Replace exception-based error handling with a Result pattern:

```python
# Current: Exception-based parsing
try:
    metadata = metadata_class(**metadata_dict)
except Exception as e:
    return ParseResult(success=False, error=f"Invalid metadata: {e}", exception=e)

# Proposed: Result pattern
class Result[T, E]:
    def __init__(self, value: T | None = None, error: E | None = None):
        self._value = value
        self._error = error

    @classmethod
    def ok(cls, value: T) -> Result[T, E]:
        return cls(value=value)

    @classmethod
    def err(cls, error: E) -> Result[T, E]:
        return cls(error=error)

    def is_ok(self) -> bool:
        return self._value is not None

    def unwrap(self) -> T:
        if self._error:
            raise RuntimeError(f"Result contains error: {self._error}")
        return self._value  # type: ignore

# Usage
def parse_metadata(metadata_dict: dict[str, Any]) -> Result[BaseMetadata, str]:
    try:
        return Result.ok(metadata_class(**metadata_dict))
    except ValidationError as e:
        return Result.err(f"Validation failed: {e}")
```

### 2. **Use Dataclasses for Simple Data Structures** (Medium Priority)
Replace some Pydantic models with dataclasses for better performance:

```python
# Current: Pydantic for everything
class BlockCandidate(BaseModel):
    syntax: BaseSyntax
    start_line: int
    lines: list[str] = Field(default_factory=list)

# Proposed: Dataclasses for internal data structures
@dataclass(frozen=True)
class BlockCandidate:
    syntax: BaseSyntax
    start_line: int
    lines: list[str] = field(default_factory=list)
    state: BlockState = BlockState.HEADER_DETECTED
    metadata_lines: list[str] = field(default_factory=list)
    content_lines: list[str] = field(default_factory=list)
    current_section: str = "header"
```

### 3. **Implement Builder Pattern for Complex Construction** (Medium Priority)
Use builders for complex object construction:

```python
# Current: Complex __init__ methods
class StreamBlockProcessor:
    def __init__(self, registry, *, logger=None, lines_buffer=5, ...):
        # 10+ parameters

# Proposed: Builder pattern
class ProcessorBuilder:
    def __init__(self, registry: Registry):
        self.registry = registry
        self._logger = None
        self._lines_buffer = 5
        # ...

    def with_logger(self, logger: Logger) -> Self:
        self._logger = logger
        return self

    def with_buffer_size(self, size: int) -> Self:
        self._lines_buffer = size
        return self

    def build(self) -> StreamBlockProcessor:
        return StreamBlockProcessor(
            registry=self.registry,
            logger=self._logger,
            lines_buffer=self._lines_buffer,
            # ...
        )

# Usage
processor = (
    ProcessorBuilder(registry)
    .with_logger(custom_logger)
    .with_buffer_size(10)
    .build()
)
```

### 4. **Reduce Code Duplication in Syntax Implementations** (Medium Priority)
Extract common parsing logic into mixins or utilities:

```python
# Current: Duplicated YAML parsing
class DelimiterFrontmatterSyntax(BaseSyntax):
    def parse_block(self, candidate, block_class=None):
        # YAML parsing logic...

class MarkdownFrontmatterSyntax(BaseSyntax):
    def parse_block(self, candidate, block_class=None):
        # Similar YAML parsing logic...

# Proposed: Mixin for YAML parsing
class YamlParserMixin:
    def _parse_yaml_metadata(self, lines: list[str]) -> dict[str, Any]:
        yaml_content = "\n".join(lines)
        return yaml.safe_load(yaml_content) or {}

class DelimiterFrontmatterSyntax(BaseSyntax, YamlParserMixin):
    def parse_block(self, candidate, block_class=None):
        metadata_dict = self._parse_yaml_metadata(candidate.metadata_lines)
        # ... rest of parsing
```

## Summary

The StreamBlocks codebase demonstrates excellent software engineering practices with strong typing, good separation of concerns, and modern Python patterns. The proposed improvements focus on:

1. **Reducing complexity** through better separation of concerns
2. **Improving type safety** with more precise and consistent typing
3. **Enhancing maintainability** through better error handling and reduced duplication
4. **Modernizing patterns** to use more idiomatic Python approaches

These changes would make the codebase more maintainable, testable, and easier to extend while preserving its current functionality and performance characteristics.