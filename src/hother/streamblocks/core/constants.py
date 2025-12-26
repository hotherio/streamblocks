"""Core constants and limits for StreamBlocks.

This module centralizes all numeric constants and default values used throughout
the library, making them easy to discover and modify if needed.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProcessingLimits:
    """Default limits for stream processing.

    These constants define the default safety limits for processing streams
    and extracting blocks. They are used as defaults in ProcessorConfig.

    Attributes:
        MAX_BLOCK_SIZE: Maximum block size in bytes (1 MiB).
            Blocks exceeding this limit are rejected to prevent memory exhaustion.
        MAX_LINE_LENGTH: Maximum line length in bytes (16 KiB).
            Lines exceeding this limit are truncated to prevent memory issues.
        HASH_PREFIX_LENGTH: Number of characters used for hash computation (64).
            Used when generating block IDs from content hash.
        LINES_BUFFER: Default number of recent lines to keep in buffer (5).
            Used for debugging and error context.
    """

    #: Maximum block size in bytes (1 MiB)
    MAX_BLOCK_SIZE: int = 1_048_576

    #: Maximum line length in bytes (16 KiB)
    MAX_LINE_LENGTH: int = 16_384

    #: Number of characters used for hash computation
    HASH_PREFIX_LENGTH: int = 64

    #: Default number of recent lines to keep in buffer
    LINES_BUFFER: int = 5


# Singleton instance for convenient access
LIMITS = ProcessingLimits()

# Type system constants
EXPECTED_BLOCK_TYPE_PARAMS = 2  # For Block[TMetadata, TContent]
