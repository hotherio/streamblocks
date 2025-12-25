"""Tests for logger module."""

from __future__ import annotations

import logging
from typing import Any
from unittest.mock import MagicMock

import pytest

from hother.streamblocks.core._logger import Logger, StdlibLoggerAdapter


class TestStdlibLoggerAdapterFormatMessage:
    """Tests for StdlibLoggerAdapter._format_message()."""

    def test_format_message_without_kwargs(self) -> None:
        """Test formatting message without kwargs returns message as-is."""
        mock_logger = MagicMock(spec=logging.Logger)
        adapter = StdlibLoggerAdapter(mock_logger)

        result = adapter._format_message("test message")

        assert result == "test message"

    def test_format_message_with_single_kwarg(self) -> None:
        """Test formatting message with single kwarg."""
        mock_logger = MagicMock(spec=logging.Logger)
        adapter = StdlibLoggerAdapter(mock_logger)

        result = adapter._format_message("test message", key="value")

        assert result == "test message | key=value"

    def test_format_message_with_multiple_kwargs(self) -> None:
        """Test formatting message with multiple kwargs (sorted alphabetically)."""
        mock_logger = MagicMock(spec=logging.Logger)
        adapter = StdlibLoggerAdapter(mock_logger)

        result = adapter._format_message("test message", zebra=1, apple=2, mango=3)

        assert result == "test message | apple=2 mango=3 zebra=1"

    def test_format_message_with_complex_values(self) -> None:
        """Test formatting message with complex values."""
        mock_logger = MagicMock(spec=logging.Logger)
        adapter = StdlibLoggerAdapter(mock_logger)

        result = adapter._format_message(
            "test",
            block_id="abc123",
            count=42,
            enabled=True,
        )

        assert "block_id=abc123" in result
        assert "count=42" in result
        assert "enabled=True" in result


class TestStdlibLoggerAdapterDebug:
    """Tests for StdlibLoggerAdapter.debug()."""

    def test_debug_without_kwargs(self) -> None:
        """Test debug logging without kwargs."""
        mock_logger = MagicMock(spec=logging.Logger)
        adapter = StdlibLoggerAdapter(mock_logger)

        adapter.debug("test message")

        mock_logger.debug.assert_called_once_with(
            "test message",
            exc_info=None,
        )

    def test_debug_with_kwargs(self) -> None:
        """Test debug logging with kwargs."""
        mock_logger = MagicMock(spec=logging.Logger)
        adapter = StdlibLoggerAdapter(mock_logger)

        adapter.debug("test message", key="value", count=5)

        mock_logger.debug.assert_called_once_with(
            "test message | count=5 key=value",
            extra={"key": "value", "count": 5},
            exc_info=None,
        )

    def test_debug_with_exc_info(self) -> None:
        """Test debug logging with exc_info."""
        mock_logger = MagicMock(spec=logging.Logger)
        adapter = StdlibLoggerAdapter(mock_logger)

        adapter.debug("error occurred", exc_info=True)

        mock_logger.debug.assert_called_once_with(
            "error occurred",
            exc_info=True,
        )

    def test_debug_with_kwargs_and_exc_info(self) -> None:
        """Test debug logging with both kwargs and exc_info."""
        mock_logger = MagicMock(spec=logging.Logger)
        adapter = StdlibLoggerAdapter(mock_logger)

        adapter.debug("error occurred", exc_info=True, block_id="123")

        mock_logger.debug.assert_called_once_with(
            "error occurred | block_id=123",
            extra={"block_id": "123"},
            exc_info=True,
        )


class TestStdlibLoggerAdapterInfo:
    """Tests for StdlibLoggerAdapter.info()."""

    def test_info_without_kwargs(self) -> None:
        """Test info logging without kwargs."""
        mock_logger = MagicMock(spec=logging.Logger)
        adapter = StdlibLoggerAdapter(mock_logger)

        adapter.info("information")

        mock_logger.info.assert_called_once_with(
            "information",
            exc_info=None,
        )

    def test_info_with_kwargs(self) -> None:
        """Test info logging with kwargs."""
        mock_logger = MagicMock(spec=logging.Logger)
        adapter = StdlibLoggerAdapter(mock_logger)

        adapter.info("block extracted", block_type="file", block_id="xyz")

        mock_logger.info.assert_called_once_with(
            "block extracted | block_id=xyz block_type=file",
            extra={"block_type": "file", "block_id": "xyz"},
            exc_info=None,
        )


class TestStdlibLoggerAdapterWarning:
    """Tests for StdlibLoggerAdapter.warning()."""

    def test_warning_without_kwargs(self) -> None:
        """Test warning logging without kwargs."""
        mock_logger = MagicMock(spec=logging.Logger)
        adapter = StdlibLoggerAdapter(mock_logger)

        adapter.warning("warning message")

        mock_logger.warning.assert_called_once_with(
            "warning message",
            exc_info=None,
        )

    def test_warning_with_kwargs(self) -> None:
        """Test warning logging with kwargs."""
        mock_logger = MagicMock(spec=logging.Logger)
        adapter = StdlibLoggerAdapter(mock_logger)

        adapter.warning("deprecated usage", feature="old_api")

        mock_logger.warning.assert_called_once_with(
            "deprecated usage | feature=old_api",
            extra={"feature": "old_api"},
            exc_info=None,
        )


class TestStdlibLoggerAdapterError:
    """Tests for StdlibLoggerAdapter.error()."""

    def test_error_without_kwargs(self) -> None:
        """Test error logging without kwargs."""
        mock_logger = MagicMock(spec=logging.Logger)
        adapter = StdlibLoggerAdapter(mock_logger)

        adapter.error("error occurred")

        mock_logger.error.assert_called_once_with(
            "error occurred",
            exc_info=None,
        )

    def test_error_with_kwargs(self) -> None:
        """Test error logging with kwargs."""
        mock_logger = MagicMock(spec=logging.Logger)
        adapter = StdlibLoggerAdapter(mock_logger)

        adapter.error("validation failed", field="email", reason="invalid format")

        mock_logger.error.assert_called_once_with(
            "validation failed | field=email reason=invalid format",
            extra={"field": "email", "reason": "invalid format"},
            exc_info=None,
        )


class TestStdlibLoggerAdapterException:
    """Tests for StdlibLoggerAdapter.exception()."""

    def test_exception_without_kwargs(self) -> None:
        """Test exception logging without kwargs."""
        mock_logger = MagicMock(spec=logging.Logger)
        adapter = StdlibLoggerAdapter(mock_logger)

        adapter.exception("exception caught")

        mock_logger.exception.assert_called_once_with(
            "exception caught",
            exc_info=True,  # Default for exception()
        )

    def test_exception_with_kwargs(self) -> None:
        """Test exception logging with kwargs."""
        mock_logger = MagicMock(spec=logging.Logger)
        adapter = StdlibLoggerAdapter(mock_logger)

        adapter.exception("parse error", block_id="123", line=42)

        mock_logger.exception.assert_called_once_with(
            "parse error | block_id=123 line=42",
            extra={"block_id": "123", "line": 42},
            exc_info=True,
        )

    def test_exception_with_exc_info_override(self) -> None:
        """Test exception logging with exc_info override."""
        mock_logger = MagicMock(spec=logging.Logger)
        adapter = StdlibLoggerAdapter(mock_logger)

        adapter.exception("error without traceback", exc_info=False)

        mock_logger.exception.assert_called_once_with(
            "error without traceback",
            exc_info=False,
        )


class TestStdlibLoggerAdapterInit:
    """Tests for StdlibLoggerAdapter initialization."""

    def test_init_stores_logger(self) -> None:
        """Test that init stores the logger reference."""
        mock_logger = MagicMock(spec=logging.Logger)
        adapter = StdlibLoggerAdapter(mock_logger)

        assert adapter._logger is mock_logger


class TestLoggerProtocol:
    """Tests for Logger protocol."""

    def test_logger_protocol_exists(self) -> None:
        """Test that Logger protocol is defined."""
        assert Logger is not None

    def test_logger_protocol_is_runtime_checkable(self) -> None:
        """Test that Logger protocol supports isinstance checks."""
        mock_logger = MagicMock(spec=logging.Logger)
        adapter = StdlibLoggerAdapter(mock_logger)

        # isinstance check should work with @runtime_checkable
        assert isinstance(adapter, Logger)

    def test_stdlib_adapter_satisfies_protocol(self) -> None:
        """Test that StdlibLoggerAdapter satisfies Logger protocol."""
        mock_logger = MagicMock(spec=logging.Logger)
        adapter = StdlibLoggerAdapter(mock_logger)

        # Protocol compliance check
        assert hasattr(adapter, "debug")
        assert hasattr(adapter, "info")
        assert hasattr(adapter, "warning")
        assert hasattr(adapter, "error")
        assert hasattr(adapter, "exception")

    def test_mock_logger_can_implement_protocol(self) -> None:
        """Test that any object with the right methods can satisfy the protocol."""

        class CustomLogger:
            def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
                pass

            def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
                pass

            def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
                pass

            def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
                pass

            def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
                pass

        logger = CustomLogger()

        # Should have all required methods
        assert callable(logger.debug)
        assert callable(logger.info)
        assert callable(logger.warning)
        assert callable(logger.error)
        assert callable(logger.exception)


class TestStdlibLoggerAdapterIntegration:
    """Integration tests for StdlibLoggerAdapter with real logger."""

    def test_with_real_stdlib_logger(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test adapter works with real stdlib logger."""
        real_logger = logging.getLogger("test_logger_integration")
        adapter = StdlibLoggerAdapter(real_logger)

        with caplog.at_level(logging.INFO):
            adapter.info("test message", key="value")

        assert "test message | key=value" in caplog.text

    def test_all_log_levels_work(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test all log levels work with real logger."""
        real_logger = logging.getLogger("test_all_levels")
        adapter = StdlibLoggerAdapter(real_logger)

        with caplog.at_level(logging.DEBUG):
            adapter.debug("debug msg", level="debug")
            adapter.info("info msg", level="info")
            adapter.warning("warning msg", level="warning")
            adapter.error("error msg", level="error")

        assert "debug msg | level=debug" in caplog.text
        assert "info msg | level=info" in caplog.text
        assert "warning msg | level=warning" in caplog.text
        assert "error msg | level=error" in caplog.text

    def test_exception_with_real_exception(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test exception logging with a real exception."""
        real_logger = logging.getLogger("test_exception")
        adapter = StdlibLoggerAdapter(real_logger)

        with caplog.at_level(logging.ERROR):
            try:
                err_msg = "test error"
                raise ValueError(err_msg)
            except ValueError:
                adapter.exception("caught error", error_type="ValueError")

        assert "caught error | error_type=ValueError" in caplog.text
        assert "ValueError: test error" in caplog.text
