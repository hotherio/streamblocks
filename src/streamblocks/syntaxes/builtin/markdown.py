"""Markdown code block syntax implementation.

This syntax handles blocks in the format:
```language
code content
```
"""

from __future__ import annotations

import contextlib
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from streamblocks.core.types import BlockState, DetectionResult
from streamblocks.syntaxes.abc import BaseSyntax

# Constants
BACKTICK_COUNT = 3
MIN_INFO_STRING_LENGTH = 1


class MarkdownCodeMetadata(BaseModel):
    """Metadata model for markdown code blocks."""

    model_config = ConfigDict(validate_assignment=True)

    language: str | None = Field(None, description="Programming language")
    filename: str | None = Field(None, description="Optional filename")
    title: str | None = Field(None, description="Optional title")
    line_numbers: bool = Field(False, description="Whether to show line numbers")
    highlight_lines: list[int] = Field(default_factory=list, description="Lines to highlight")
    attributes: dict[str, str] = Field(default_factory=dict, description="Additional attributes")


class MarkdownCodeContent(BaseModel):
    """Content model for markdown code blocks."""

    model_config = ConfigDict(validate_assignment=True)

    code: str = Field(description="The code content")
    line_count: int = Field(default=0, description="Number of lines")
    has_trailing_newline: bool = Field(True, description="Whether code ends with newline")

    def __init__(self, **data: Any) -> None:
        """Initialize with computed fields."""
        super().__init__(**data)
        if "line_count" not in data and "code" in data:
            self.line_count = len(data["code"].splitlines())
        if "has_trailing_newline" not in data and "code" in data:
            self.has_trailing_newline = data["code"].endswith("\n")


class MarkdownCodeSyntax(BaseSyntax[MarkdownCodeMetadata, MarkdownCodeContent]):
    """Markdown code block syntax parser.

    Handles blocks like:
    ```python
    def hello():
        print("Hello, World!")
    ```

    Or with additional metadata:
    ```javascript {filename: "app.js", highlight: [2, 3]}
    const app = express();
    app.get('/', handler);
    app.listen(3000);
    ```
    """

    @property
    def name(self) -> str:
        """Syntax identifier."""
        return "markdown-code"

    def detect_line(self, line: str, context: Any = None) -> DetectionResult:
        """Detect markdown code block boundaries."""
        from streamblocks.core.models import BlockCandidate

        stripped = line.strip()

        # Check for code fence
        if not self._is_code_fence(stripped):
            return DetectionResult()

        # Opening fence (no context)
        if context is None:
            # Extract language and metadata from info string
            info_string = self._extract_info_string(stripped)
            metadata = self._parse_info_string(info_string) if info_string else {}
            return DetectionResult(is_opening=True, metadata=metadata)

        # Closing fence (in content accumulation)
        if isinstance(context, BlockCandidate) and context.state == BlockState.ACCUMULATING_CONTENT:
            return DetectionResult(is_closing=True)

        return DetectionResult()

    def should_accumulate_metadata(self, candidate: Any) -> bool:
        """Markdown code blocks have inline metadata only."""
        return False

    def parse_block(self, candidate: Any) -> Any:
        """Parse markdown code block into metadata and content."""
        from streamblocks.core.models import BlockCandidate
        from streamblocks.core.types import ParseResult

        if not isinstance(candidate, BlockCandidate):
            return ParseResult[MarkdownCodeMetadata, MarkdownCodeContent](
                success=False,
                error="Invalid candidate type"
            )

        try:
            # Parse metadata from the stored metadata dict
            metadata = self._create_metadata(candidate.metadata)

            # Get code content (excluding fence lines)
            code_lines = candidate.content_lines
            code = "\n".join(code_lines)

            # Create content model
            content = MarkdownCodeContent(code=code)

            # Validate
            if not self.validate_block(metadata, content):
                return ParseResult[MarkdownCodeMetadata, MarkdownCodeContent](
                    success=False,
                    error="Block validation failed"
                )

            return ParseResult[MarkdownCodeMetadata, MarkdownCodeContent](
                success=True,
                metadata=metadata,
                content=content
            )

        except Exception as e:
            return ParseResult[MarkdownCodeMetadata, MarkdownCodeContent](
                success=False,
                error=f"Parse error: {e}"
            )

    def get_opening_pattern(self) -> str | None:
        """Pattern for opening code fence."""
        return r"^```.*$"

    def get_closing_pattern(self) -> str | None:
        """Pattern for closing code fence."""
        return r"^```\s*$"

    def get_block_type_hints(self) -> list[str]:
        """Get list of block types this syntax typically produces."""
        return ["code", "markdown-code", "fenced-code"]

    def validate_block(self, metadata: MarkdownCodeMetadata, content: MarkdownCodeContent) -> bool:
        """Validate parsed block."""
        # Code blocks are generally valid as long as they parse
        return True

    # Helper methods

    def _is_code_fence(self, line: str) -> bool:
        """Check if line is a code fence (```)."""
        return line.startswith("```")

    def _extract_info_string(self, fence_line: str) -> str:
        """Extract info string from opening fence line."""
        # Remove the ``` prefix
        if fence_line.startswith("```"):
            return fence_line[BACKTICK_COUNT:].strip()
        return ""

    def _parse_info_string(self, info_string: str) -> dict[str, Any]:
        """Parse info string into metadata components."""
        if not info_string:
            return {}

        metadata: dict[str, Any] = {}

        # Common patterns:
        # 1. Simple: "python"
        # 2. With filename: "python filename.py"
        # 3. With attributes: "python {highlight: [1, 2]}"
        # 4. Complex: "python filename.py {highlight: [1, 2], title: 'Example'}"

        # Check for attributes in curly braces
        attr_match = re.search(r"\{(.+)\}$", info_string)
        if attr_match:
            # Extract and parse attributes
            attr_str = attr_match.group(1)
            info_string = info_string[:attr_match.start()].strip()

            # Simple attribute parsing (not full JSON)
            # Parse by manually tracking brackets
            try:
                i = 0
                while i < len(attr_str):
                    # Find key
                    key_start = i
                    while i < len(attr_str) and attr_str[i] not in ":,}":
                        i += 1

                    if i >= len(attr_str) or attr_str[i] != ":":
                        break

                    key = attr_str[key_start:i].strip().strip("'\"")
                    i += 1  # Skip ':'

                    # Find value - handle arrays specially
                    while i < len(attr_str) and attr_str[i] == " ":
                        i += 1

                    value_start = i
                    if i < len(attr_str) and attr_str[i] == "[":
                        # Array value - find matching ]
                        bracket_count = 1
                        i += 1
                        while i < len(attr_str) and bracket_count > 0:
                            if attr_str[i] == "[":
                                bracket_count += 1
                            elif attr_str[i] == "]":
                                bracket_count -= 1
                            i += 1
                    else:
                        # Regular value - find next comma or end
                        while i < len(attr_str) and attr_str[i] not in ",}":
                            i += 1

                    value = attr_str[value_start:i].strip().strip("'\"")

                    # Skip comma if present
                    while i < len(attr_str) and attr_str[i] in ", ":
                        i += 1

                    # Process the key-value pair
                    if key == "highlight":
                        if value.startswith("[") and value.endswith("]"):
                            numbers = value[1:-1].split(",")
                            metadata["highlight_lines"] = [int(n.strip()) for n in numbers if n.strip().isdigit()]
                        elif value.strip():
                            with contextlib.suppress(ValueError):
                                metadata["highlight_lines"] = [int(value.strip())]
                    elif key == "line-numbers":
                        metadata["line_numbers"] = value.lower() in ("true", "yes", "1")
                    elif key == "title":
                        metadata["title"] = value
                    else:
                        if "attributes" not in metadata:
                            metadata["attributes"] = {}
                        metadata["attributes"][key] = value
            except Exception:
                # Ignore parsing errors in attributes
                pass

        # Parse remaining info string (language and optional filename)
        parts = info_string.split(None, 1)  # Split on first whitespace

        if parts:
            # First part is always language
            metadata["language"] = parts[0]

            # Second part (if any) is typically filename
            if len(parts) > 1:
                metadata["filename"] = parts[1]

        return metadata

    def _create_metadata(self, metadata_dict: dict[str, Any]) -> MarkdownCodeMetadata:
        """Create metadata model from parsed dictionary."""
        return MarkdownCodeMetadata(
            language=metadata_dict.get("language"),
            filename=metadata_dict.get("filename"),
            title=metadata_dict.get("title"),
            line_numbers=metadata_dict.get("line_numbers", False),
            highlight_lines=metadata_dict.get("highlight_lines", []),
            attributes=metadata_dict.get("attributes", {})
        )
