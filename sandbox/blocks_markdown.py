#!/usr/bin/env python3
"""
Async, minimal, self-contained frontmatter splitter for Python 3.13.
Works on any partial stream that ends on a complete line.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, AsyncIterable


async def split_frontmatter_stream(
    stream: AsyncIterable[str],
) -> AsyncGenerator[tuple[dict[str, str], str]]:
    """
    Async generator that yields (metadata, content) tuples as soon as
    the closing `---` of the frontmatter is detected.

    Parameters
    ----------
    stream : AsyncIterable[str]
        Async source of text chunks, each chunk ending on a complete line.

    Yields
    ------
    Tuple[Dict[str, str], str]
        (metadata, content) – content may be empty until the closing `---`
        arrives; afterwards every new chunk is yielded immediately as
        ({}, additional_content).
    """
    buf: list[str] = []
    meta_parsed = False
    meta: dict[str, str] = {}

    async for chunk in stream:
        buf.append(chunk)
        if not meta_parsed:
            # check if we now have a complete frontmatter block
            text = "".join(buf)
            lines = text.splitlines(keepends=True)

            min_lines_for_frontmatter = 2
            if len(lines) >= min_lines_for_frontmatter and lines[0].rstrip() == "---":
                try:
                    close_idx = next(i for i, line in enumerate(lines[1:], 1) if line.rstrip() == "---")
                except StopIteration:
                    continue  # still waiting for closing ---

                # parse metadata
                for line in lines[1:close_idx]:
                    if ":" not in line:
                        continue
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()

                # yield first (meta, content) pair
                content = "".join(lines[close_idx + 1 :])
                yield meta, content
                meta_parsed = True
                buf = [content]  # keep any leftover content for next yield
        else:
            # frontmatter already done; just forward new content
            yield {}, chunk


# ------------------------------------------------------------------
# Quick demo / self-test
# ------------------------------------------------------------------
async def _demo() -> None:
    async def fake_stream() -> AsyncGenerator[str]:
        chunks = [
            "---\nid: file01\n",
            "name: files_operations\n---\n",
            "src/main.py:C\n",
            "src/utils.py:C\nREADME.md:E\n",
        ]
        for c in chunks:
            yield c
            await asyncio.sleep(0.01)  # simulate I/O

    async for meta, content in split_frontmatter_stream(fake_stream()):
        print("META:", meta)
        print("CONTENT:", repr(content))


if __name__ == "__main__":
    asyncio.run(_demo())
