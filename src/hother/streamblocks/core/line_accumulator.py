"""Line accumulation utilities for StreamBlocks."""

from __future__ import annotations

from collections import deque


class LineAccumulator:
    """Accumulates text chunks and yields complete lines.

    This class handles the conversion of arbitrary text chunks into
    complete lines, managing partial line buffering and line counting.

    Example:
        >>> accumulator = LineAccumulator(max_line_length=100, buffer_size=5)
        >>> lines = accumulator.add_text("Hello\\nWor")
        >>> print(lines)  # ["Hello"]
        >>> lines = accumulator.add_text("ld\\n")
        >>> print(lines)  # ["World"]
        >>> final = accumulator.finalize()
        >>> print(final)  # None (no incomplete text)
    """

    def __init__(
        self,
        max_line_length: int = 16_384,
        buffer_size: int = 5,
    ) -> None:
        """Initialize the line accumulator.

        Args:
            max_line_length: Maximum line length before truncation
            buffer_size: Number of recent lines to keep in buffer
        """
        self._max_line_length = max_line_length
        self._accumulated_text: list[str] = []
        self._accumulated_length = 0
        self._line_counter = 0
        self._buffer: deque[str] = deque(maxlen=buffer_size)

    @property
    def line_number(self) -> int:
        """Get the current line number (1-indexed after first line processed)."""
        return self._line_counter

    @property
    def buffer(self) -> list[str]:
        """Get the recent lines buffer as a list."""
        return list(self._buffer)

    @property
    def has_pending_text(self) -> bool:
        """Check if there's accumulated text waiting for a newline."""
        return len(self._accumulated_text) > 0

    def add_text(self, text: str) -> list[tuple[int, str]]:
        """Add text and return complete lines.

        Accumulates text until newlines are found, then returns complete lines.
        Incomplete lines (text without trailing newline) are buffered for the
        next call or finalize(). A trailing ``\\r`` is stripped, and the pending
        buffer never grows beyond ``max_line_length``.

        Args:
            text: Text to add (may contain newlines)

        Returns:
            List of tuples (line_number, line_content) for each complete line.
            Line numbers are 1-indexed.
        """
        *complete, tail = text.split("\n")
        if not complete:
            self._accumulate(tail)
            return []

        self._accumulate(complete[0])
        complete[0] = self._take_pending()
        self._accumulate(tail)
        return [self._emit(line) for line in complete]

    def _accumulate(self, text: str) -> None:
        room = self._max_line_length - self._accumulated_length
        if text and room > 0:
            self._accumulated_text.append(text[:room])
            self._accumulated_length += min(len(text), room)

    def _take_pending(self) -> str:
        pending = "".join(self._accumulated_text)
        self._accumulated_text.clear()
        self._accumulated_length = 0
        return pending

    def _emit(self, line: str) -> tuple[int, str]:
        line = line[: self._max_line_length].removesuffix("\r")
        self._line_counter += 1
        self._buffer.append(line)
        return (self._line_counter, line)

    def finalize(self) -> tuple[int, str] | None:
        """Finalize and return any remaining incomplete text as a final line.

        Call this at the end of stream processing to handle text that
        doesn't end with a newline.

        Returns:
            Tuple of (line_number, line_content) if there was incomplete text,
            None otherwise.
        """
        if not self._accumulated_text:
            return None
        return self._emit(self._take_pending())

    def reset(self) -> None:
        """Reset the accumulator state.

        Clears all accumulated text, resets line counter, and clears buffer.
        """
        self._take_pending()
        self._line_counter = 0
        self._buffer.clear()
