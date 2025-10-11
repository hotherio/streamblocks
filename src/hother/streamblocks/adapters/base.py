"""Base protocol for stream adapters."""

from __future__ import annotations

from typing import Any, Protocol, TypeVar, runtime_checkable

TChunk = TypeVar("TChunk", contravariant=True)


@runtime_checkable
class StreamAdapter(Protocol[TChunk]):
    """Protocol for extracting text from stream chunks.

    Adapters convert provider-specific chunk formats (Gemini, OpenAI, etc.)
    into text that can be processed by StreamBlocks while preserving
    the original chunks for transparency.

    Example:
        >>> adapter = GeminiAdapter()
        >>> text = adapter.extract_text(gemini_chunk)
        >>> if text:
        ...     print(f"Got text: {text}")
    """

    def extract_text(self, chunk: TChunk) -> str | None:
        """Extract text content from a chunk.

        Args:
            chunk: Provider-specific chunk object

        Returns:
            Extracted text, or None if chunk contains no text

        Example:
            >>> adapter = GeminiAdapter()
            >>> adapter.extract_text(gemini_chunk)
            "Hello world"
        """
        ...

    def is_complete(self, chunk: TChunk) -> bool:
        """Check if this chunk signals stream completion.

        Args:
            chunk: Provider-specific chunk object

        Returns:
            True if this is the final chunk

        Example:
            >>> adapter.is_complete(chunk)
            False
        """
        ...

    def get_metadata(self, chunk: TChunk) -> dict[str, Any] | None:
        """Extract metadata from chunk (optional).

        This can be used to enrich StreamBlocks events with
        provider-specific metadata like token counts, model info, etc.

        Args:
            chunk: Provider-specific chunk object

        Returns:
            Dictionary of metadata, or None

        Example:
            >>> metadata = adapter.get_metadata(chunk)
            >>> if metadata and 'usage' in metadata:
            ...     print(f"Tokens used: {metadata['usage']}")
        """
        return None
