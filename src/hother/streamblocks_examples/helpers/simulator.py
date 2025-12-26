"""Stream simulation helpers using cancelable library.

This module provides simplified wrappers around hother-cancelable's simulate_stream
for use in StreamBlocks examples.
"""

import asyncio
from collections.abc import AsyncIterator
from typing import Any

try:
    from hother.cancelable.streaming.simulator import StreamConfig, simulate_stream

    SIMULATOR_AVAILABLE = True
except ImportError:
    SIMULATOR_AVAILABLE = False
    StreamConfig = None  # type: ignore[misc, assignment]
    simulate_stream = None  # type: ignore[misc, assignment]


# Preset configurations
class StreamPresets:
    """Preset stream configurations for common use cases."""

    INSTANT = (
        StreamConfig(
            chunk_size=1000,
            base_delay=0.0,
            jitter_probability=0.0,
            burst_probability=0.0,
            stall_probability=0.0,
        )
        if SIMULATOR_AVAILABLE
        else None
    )

    FAST = (
        StreamConfig(
            chunk_size=50,
            base_delay=0.01,
            jitter=0.005,
            jitter_probability=0.2,
            burst_probability=0.0,
            stall_probability=0.0,
        )
        if SIMULATOR_AVAILABLE
        else None
    )

    REALISTIC = (
        StreamConfig(
            chunk_size=20,
            base_delay=0.05,
            jitter=0.02,
            jitter_probability=0.3,
            burst_probability=0.1,
            burst_size=3,
            stall_probability=0.05,
            stall_duration=0.2,
        )
        if SIMULATOR_AVAILABLE
        else None
    )

    VARIABLE_CHUNKS = (
        StreamConfig(
            chunk_size=30,
            base_delay=0.02,
            variable_chunk_size=True,
            chunk_size_range=(10, 50),
        )
        if SIMULATOR_AVAILABLE
        else None
    )


async def simulated_stream(
    text: str,
    preset: str = "fast",
    config: Any = None,  # StreamConfig type
) -> AsyncIterator[str]:
    """Create a simulated text stream with realistic timing.

    This function wraps simulate_stream from hother-cancelable and extracts
    just the text chunks, making it a drop-in replacement for manual stream
    functions in examples.

    Args:
        text: The text content to stream
        preset: Preset configuration name ("instant", "fast", "realistic", "variable")
        config: Optional custom StreamConfig (overrides preset)

    Yields:
        Text chunks as strings

    Example:
        >>> async def main():
        ...     async for chunk in simulated_stream("Hello world", preset="fast"):
        ...         print(chunk, end="")
    """
    if not SIMULATOR_AVAILABLE:
        # Fallback: yield entire text as single chunk
        yield text
        return

    # Select configuration
    if config is None:
        preset_map = {
            "instant": StreamPresets.INSTANT,
            "fast": StreamPresets.FAST,
            "realistic": StreamPresets.REALISTIC,
            "variable": StreamPresets.VARIABLE_CHUNKS,
        }
        config = preset_map.get(preset, StreamPresets.FAST)

    # Stream with simulation
    async for event in simulate_stream(text, config=config):
        # Extract only data events with text chunks
        if isinstance(event, dict) and event.get("type") == "data":
            chunk = event.get("chunk")
            if chunk:
                yield chunk


async def chunked_text_stream(
    text: str,
    chunk_size: int = 30,
    delay: float = 0.01,
) -> AsyncIterator[str]:
    """Simple chunked stream with fixed chunk size and delay.

    This provides a simpler alternative to simulated_stream when you just
    need fixed-size chunks without network simulation.

    Args:
        text: The text to stream
        chunk_size: Size of each chunk in characters
        delay: Delay between chunks in seconds

    Yields:
        Text chunks as strings
    """
    if SIMULATOR_AVAILABLE:
        config = StreamConfig(
            chunk_size=chunk_size,
            base_delay=delay,
            jitter_probability=0.0,
            burst_probability=0.0,
            stall_probability=0.0,
        )
        async for chunk in simulated_stream(text, config=config):
            yield chunk
    else:
        # Fallback implementation
        for i in range(0, len(text), chunk_size):
            yield text[i : i + chunk_size]
            if delay > 0:
                await asyncio.sleep(delay)


async def simple_text_stream(text: str) -> AsyncIterator[str]:
    """Yield text as a single chunk (instant delivery).

    Backward compatible replacement for simple stream() functions.

    Args:
        text: The text to stream

    Yields:
        Text chunks as strings
    """
    async for chunk in simulated_stream(text, preset="instant"):
        yield chunk


__all__ = [
    "SIMULATOR_AVAILABLE",
    "StreamConfig",
    "StreamPresets",
    "chunked_text_stream",
    "simple_text_stream",
    "simulated_stream",
]
