"""Delimiter preamble syntax implementation.

This syntax handles blocks in the format:
!!block123:type:params
Content goes here
!!end
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from streamblocks.core.models import BlockCandidate
from streamblocks.core.types import BlockState, DetectionResult
from streamblocks.syntaxes.abc import DelimiterSyntax

if TYPE_CHECKING:
    from pydantic import BaseModel


# Constants
DELIMITER_PARTS_MIN = 2


class DelimiterPreambleSyntax[TMetadata: BaseModel, TContent: BaseModel](
    DelimiterSyntax[TMetadata, TContent]
):
    """Delimiter preamble syntax parser.

    This is a generic syntax parser for delimiter-based blocks with inline metadata.
    Users must provide their own metadata and content model classes.

    Format:
    !!id:type[:params...]
    content
    !!end

    Example usage:
    ```python
    class MyMetadata(BaseModel):
        id: str
        type: str
        params: str | None = None

    class MyContent(BaseModel):
        text: str

    syntax = DelimiterPreambleSyntax(
        metadata_class=MyMetadata,
        content_class=MyContent,
        prefix="!!",
        end_suffix=":end"
    )
    ```
    """

    def __init__(
        self,
        metadata_class: type[TMetadata],
        content_class: type[TContent],
        prefix: str = "!!",
        end_suffix: str = ":end",
    ) -> None:
        """Initialize with user-provided model classes.

        Args:
            metadata_class: Pydantic model class for metadata
            content_class: Pydantic model class for content
            prefix: Delimiter prefix (default: "!!")
            end_suffix: Suffix for end delimiter (default: ":end")
        """
        self.metadata_class = metadata_class
        self.content_class = content_class
        self._prefix = prefix
        self._end_suffix = end_suffix

    @property
    def name(self) -> str:
        """Syntax identifier."""
        return f"delimiter_preamble_{self._prefix}"

    @property
    def delimiter_prefix(self) -> str:
        """Prefix for block delimiters."""
        return self._prefix

    @property
    def end_suffix(self) -> str:
        """Suffix for end delimiter."""
        return self._end_suffix

    def detect_line(self, line: str, context: Any = None) -> DetectionResult:
        """Enhanced detection for delimiter blocks."""
        stripped = line.strip()

        # Check for opening marker
        if context is None:
            if stripped.startswith(self.delimiter_prefix):
                # Extract metadata from opening line
                metadata = self._extract_inline_metadata(stripped)
                if metadata:
                    return DetectionResult(is_opening=True, metadata=metadata)
            return DetectionResult()

        # Check for closing marker
        if (
            isinstance(context, BlockCandidate)
            and context.state == BlockState.ACCUMULATING_CONTENT
            and (stripped == f"{self.delimiter_prefix}end" or stripped.endswith(self.end_suffix))
        ):
            return DetectionResult(is_closing=True)

        return DetectionResult()

    def _extract_inline_metadata(self, opening_line: str) -> dict[str, Any]:
        """Extract metadata from opening delimiter line."""
        # Remove prefix
        line = opening_line.strip()
        if line.startswith(self.delimiter_prefix):
            line = line[len(self.delimiter_prefix) :]

        # Check if this is just "end" marker
        if line == "end" or line.endswith(self.end_suffix):
            return {}

        # Parse the preamble - implementation depends on user's metadata model
        # We'll provide the raw preamble data and let the metadata class handle it
        return {"_raw_preamble": line}

    def parse_metadata_dict(self, metadata_dict: dict[str, Any]) -> TMetadata:
        """Convert metadata dictionary to typed metadata model."""
        # Handle raw preamble parsing
        if "_raw_preamble" in metadata_dict:
            preamble = metadata_dict.pop("_raw_preamble")
            # Basic parsing strategy: split by colons
            parts = preamble.split(":")

            # Try to map common patterns to metadata fields
            # This is a best-effort approach - users can override for custom parsing
            if hasattr(self.metadata_class, "model_fields"):
                fields = self.metadata_class.model_fields
                if "id" in fields and len(parts) >= 1:
                    metadata_dict["id"] = parts[0]
                if "type" in fields and len(parts) >= DELIMITER_PARTS_MIN:
                    metadata_dict["type"] = parts[1]
                # Any remaining parts could be params, args, etc.
                if len(parts) > DELIMITER_PARTS_MIN:
                    # Look for common field names
                    for field_name in ["params", "args", "options", "extra"]:
                        if field_name in fields:
                            metadata_dict[field_name] = ":".join(parts[2:])
                            break

        # Let the metadata class handle validation
        return self.metadata_class(**metadata_dict)

    def parse_content(self, content_text: str) -> TContent:
        """Parse content text into content model."""
        # Try different initialization strategies
        if hasattr(self.content_class, "parse"):
            # If content class has a parse method, use it
            return self.content_class.parse(content_text)  # type: ignore[attr-defined, no-any-return]

        # Try common field names
        init_kwargs: dict[str, Any] = {}
        if hasattr(self.content_class, "model_fields"):
            fields = self.content_class.model_fields
            # Try common content field names
            for field_name in ["text", "content", "raw", "body", "data"]:
                if field_name in fields:
                    init_kwargs[field_name] = content_text
                    break

        if not init_kwargs:
            # Fallback: try to initialize with positional argument
            try:
                return self.content_class(content_text)  # type: ignore[call-arg]
            except Exception:
                # Last resort: empty initialization
                init_kwargs = {}

        return self.content_class(**init_kwargs)

    def get_block_type_hints(self) -> list[str]:
        """Get list of block types this syntax typically produces."""
        # Try to infer from metadata class
        if hasattr(self.metadata_class, "model_fields"):
            fields = self.metadata_class.model_fields
            if "type" in fields:
                # Could potentially extract literal types or enums here
                return ["block"]
        return ["block"]

    def supports_nested_blocks(self) -> bool:
        """Delimiter blocks can support nesting with different IDs."""
        return True

    def validate_block(self, metadata: TMetadata, content: TContent) -> bool:
        """Validate parsed block."""
        # Delegate validation to user's models
        # The models themselves should have validators
        return True
