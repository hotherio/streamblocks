"""Exception hierarchy raised by :mod:`hother.streamblocks`.

A single base class :class:`StreamblocksError` with one level of subclasses;
consumers can catch the base or a specific subclass without chasing deep
inheritance trees.

These exceptions are raised **synchronously** to signal programmer or
configuration errors (an adapter was not configured, no adapter could be
detected for a chunk type, an invalid syntax argument was passed). They abort
the call that hit them.

They are deliberately distinct from the per-block *runtime* error reporting in
the stream: :class:`~hother.streamblocks.core.types.BlockErrorEvent` (carrying a
:class:`~hother.streamblocks.core.types.BlockErrorCode`) is emitted **as data**
into the event stream when an individual block fails to validate, exceeds the
size limit, or is left unclosed. Stream-level, per-block problems stay events;
misuse and impossible internal state become exceptions. Do not collapse the two.
"""


class StreamblocksError(Exception):
    """Base class for all exceptions raised by ``hother.streamblocks``."""


class AdapterNotConfiguredError(StreamblocksError):
    """Raised when the input adapter is missing after first-chunk processing.

    This signals an impossible internal state: by the time a chunk's text is
    extracted, auto-detection should already have set an adapter.

    Attributes:
        context: The processing entry point where the missing adapter was
            observed (e.g. ``"process_chunk"``, ``"process_stream"``,
            ``"protocol_processor"``).
    """

    context: str

    def __init__(self, *, context: str) -> None:
        detail = "This indicates an internal state error."
        message = f"Input adapter is not configured after first-chunk processing (context: {context}). {detail}"
        super().__init__(message)
        self.context = context


class AdapterDetectionError(StreamblocksError):
    """Raised when no input adapter can be auto-detected for a chunk type.

    Attributes:
        chunk_type: The fully-qualified type name of the unrecognised chunk
            (e.g. ``"openai.types.ChatCompletionChunk"``).
        registered_prefixes: The module prefixes currently registered for
            auto-detection.
    """

    chunk_type: str
    registered_prefixes: tuple[str, ...]

    def __init__(self, *, chunk_type: str, registered_prefixes: tuple[str, ...]) -> None:
        prefixes = list(registered_prefixes)
        hint = "Consider importing the appropriate extension or registering a custom adapter."
        message = f"No input adapter found for {chunk_type}. Registered module prefixes: {prefixes}. {hint}"
        super().__init__(message)
        self.chunk_type = chunk_type
        self.registered_prefixes = registered_prefixes


class SyntaxConfigError(StreamblocksError):
    """Raised when a syntax argument is neither a ``Syntax`` enum nor a ``BaseSyntax``.

    Attributes:
        received_type: The name of the type that was passed instead.
    """

    received_type: str

    def __init__(self, *, received_type: str) -> None:
        super().__init__(f"Expected a Syntax enum member or BaseSyntax instance, got {received_type}.")
        self.received_type = received_type


__all__ = [
    "AdapterDetectionError",
    "AdapterNotConfiguredError",
    "StreamblocksError",
    "SyntaxConfigError",
]
