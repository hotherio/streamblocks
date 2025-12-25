"""Common stream generators for examples."""

import asyncio
from collections.abc import AsyncIterator
from textwrap import dedent


async def simple_stream(text: str | None = None) -> AsyncIterator[str]:
    """Yield text as a single chunk.

    Args:
        text: Text to yield. If None, uses a default example.
    """
    if text is None:
        text = dedent("""
            !!block01:files_operations
            src/main.py:C
            src/utils.py:C
            !!end
        """)
    yield text


async def chunked_stream(
    text: str | None = None,
    chunk_size: int = 30,
    delay: float = 0.01,
) -> AsyncIterator[str]:
    """Yield text in chunks to simulate streaming.

    Args:
        text: Text to chunk. If None, uses a default example.
        chunk_size: Size of each chunk in characters.
        delay: Delay between chunks in seconds.
    """
    if text is None:
        text = dedent("""
            Some introductory text.

            !!block01:files_operations
            src/main.py:C
            src/utils.py:C
            !!end

            Some text between blocks.

            !!block02:files_operations
            tests/test_main.py:C
            !!end

            Final text.
        """)

    for i in range(0, len(text), chunk_size):
        yield text[i : i + chunk_size]
        await asyncio.sleep(delay)
