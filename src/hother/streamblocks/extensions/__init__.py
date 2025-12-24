"""StreamBlocks extensions for various protocols and providers.

Extensions provide input/output adapters for specific protocols:
- openai: OpenAI ChatCompletionChunk streams
- anthropic: Anthropic message streams
- gemini: Google GenAI streams
- agui: AG-UI protocol events

Each extension self-registers its adapters for auto-detection when imported.

Example:
    >>> # Import extension to enable auto-detection
    >>> import hother.streamblocks.extensions.openai
    >>>
    >>> # Now auto-detection works for OpenAI streams
    >>> processor = ProtocolStreamProcessor(registry)
    >>> async for event in processor.process_stream(openai_stream):
    ...     print(event)
"""

__all__: list[str] = []
