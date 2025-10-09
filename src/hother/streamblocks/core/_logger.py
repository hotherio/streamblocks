"""Logger protocol for StreamBlocks.

StreamBlocks accepts any logger that implements the standard Python logging interface.
This includes stdlib logging, structlog, loguru, or any custom logger.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    import logging


class StdlibLoggerAdapter:
    """Adapter for stdlib logging that converts kwargs to extra dict and displays them.

    StreamBlocks uses direct keyword arguments for structured logging (the pattern
    used by structlog and loguru), but stdlib logging requires them in an 'extra' dict.
    This adapter automatically:
    1. Appends structured data to the log message for visibility
    2. Stores data in 'extra' dict for programmatic access

    Example:
        >>> import logging
        >>> from hother.streamblocks.core._logger import StdlibLoggerAdapter
        >>>
        >>> stdlib_logger = logging.getLogger(__name__)
        >>> logger = StdlibLoggerAdapter(stdlib_logger)
        >>>
        >>> # Now you can use direct kwargs like structlog/loguru
        >>> logger.info("block_extracted", block_type="files", block_id="abc123")
        >>> # Output: "INFO - block_extracted | block_id=abc123 block_type=files"
    """

    def __init__(self, logger: logging.Logger) -> None:
        """Initialize adapter with a stdlib logger.

        Args:
            logger: A stdlib logging.Logger instance
        """
        self._logger = logger

    def _format_message(self, msg: str, **kwargs: Any) -> str:
        """Format message with structured data appended.

        Args:
            msg: Base log message
            **kwargs: Structured data fields

        Returns:
            Formatted message with "msg | key1=value1 key2=value2" format
        """
        if not kwargs:
            return msg

        # Sort keys for consistent output
        fields = " ".join(f"{k}={v}" for k, v in sorted(kwargs.items()))
        return f"{msg} | {fields}"

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log debug message with kwargs converted to extra dict."""
        exc_info = kwargs.pop("exc_info", None)
        formatted_msg = self._format_message(msg, **kwargs)
        if kwargs:
            self._logger.debug(formatted_msg, *args, extra=kwargs, exc_info=exc_info)
        else:
            self._logger.debug(formatted_msg, *args, exc_info=exc_info)

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log info message with kwargs converted to extra dict."""
        exc_info = kwargs.pop("exc_info", None)
        formatted_msg = self._format_message(msg, **kwargs)
        if kwargs:
            self._logger.info(formatted_msg, *args, extra=kwargs, exc_info=exc_info)
        else:
            self._logger.info(formatted_msg, *args, exc_info=exc_info)

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log warning message with kwargs converted to extra dict."""
        exc_info = kwargs.pop("exc_info", None)
        formatted_msg = self._format_message(msg, **kwargs)
        if kwargs:
            self._logger.warning(formatted_msg, *args, extra=kwargs, exc_info=exc_info)
        else:
            self._logger.warning(formatted_msg, *args, exc_info=exc_info)

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log error message with kwargs converted to extra dict."""
        exc_info = kwargs.pop("exc_info", None)
        formatted_msg = self._format_message(msg, **kwargs)
        if kwargs:
            self._logger.error(formatted_msg, *args, extra=kwargs, exc_info=exc_info)
        else:
            self._logger.error(formatted_msg, *args, exc_info=exc_info)

    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log exception with traceback and kwargs converted to extra dict."""
        # exception() always sets exc_info=True by default, but allow override
        exc_info = kwargs.pop("exc_info", True)
        formatted_msg = self._format_message(msg, **kwargs)
        if kwargs:
            self._logger.exception(formatted_msg, *args, extra=kwargs, exc_info=exc_info)
        else:
            self._logger.exception(formatted_msg, *args, exc_info=exc_info)


class Logger(Protocol):
    """Anything that looks like a logger is a logger.

    StreamBlocks uses direct keyword arguments for structured logging:
        logger.info("block_extracted", block_type="files", block_id="abc123")

    This is the native pattern for structlog and loguru. For stdlib logging,
    use StdlibLoggerAdapter to convert kwargs to the extra dict format.

    Compatible with:
    - logging.Logger (stdlib) via StdlibLoggerAdapter
    - structlog loggers (native kwargs support)
    - loguru.Logger (native kwargs support)
    - Any custom logger with these methods

    Example with stdlib logging:
        >>> import logging
        >>> from hother.streamblocks import StreamBlockProcessor
        >>> from hother.streamblocks.core._logger import StdlibLoggerAdapter
        >>>
        >>> stdlib_logger = logging.getLogger("my_app.streamblocks")
        >>> logger = StdlibLoggerAdapter(stdlib_logger)
        >>> processor = StreamBlockProcessor(registry=registry, logger=logger)

    Example with structlog:
        >>> import structlog
        >>> logger = structlog.get_logger("streamblocks")
        >>> processor = StreamBlockProcessor(registry=registry, logger=logger)

    Example with loguru:
        >>> from loguru import logger
        >>> processor = StreamBlockProcessor(registry=registry, logger=logger)
    """

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> Any:
        """Log debug message.

        Args:
            msg: Message to log
            *args: Positional arguments for message formatting
            **kwargs: Structured data as direct keyword arguments (e.g., block_type="files")
        """
        ...

    def info(self, msg: str, *args: Any, **kwargs: Any) -> Any:
        """Log info message.

        Args:
            msg: Message to log
            *args: Positional arguments for message formatting
            **kwargs: Structured data as direct keyword arguments (e.g., block_type="files")
        """
        ...

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> Any:
        """Log warning message.

        Args:
            msg: Message to log
            *args: Positional arguments for message formatting
            **kwargs: Structured data as direct keyword arguments (e.g., block_type="files")
        """
        ...

    def error(self, msg: str, *args: Any, **kwargs: Any) -> Any:
        """Log error message.

        Args:
            msg: Message to log
            *args: Positional arguments for message formatting
            **kwargs: Structured data as direct keyword arguments (e.g., block_type="files")
        """
        ...

    def exception(self, msg: str, *args: Any, **kwargs: Any) -> Any:
        """Log exception with traceback.

        Args:
            msg: Message to log
            *args: Positional arguments for message formatting
            **kwargs: Structured data as direct keyword arguments (e.g., block_type="files")
        """
        ...
