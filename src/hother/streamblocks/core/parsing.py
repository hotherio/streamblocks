"""Parsing decorators for content models."""

from __future__ import annotations

import json
from enum import StrEnum, auto
from typing import TYPE_CHECKING, Any

import yaml
from pydantic import ValidationError

from hother.streamblocks.core.types import BaseContent

if TYPE_CHECKING:
    from collections.abc import Callable


class ParseStrategy(StrEnum):
    """Strategy for handling parsing errors."""

    STRICT = auto()  # Raise exception on parse error
    PERMISSIVE = auto()  # Fall back to raw_content on error


def parse_as_yaml[T: BaseContent](
    *,
    strategy: ParseStrategy = ParseStrategy.PERMISSIVE,
    handle_non_dict: bool = True,
) -> Callable[[type[T]], type[T]]:
    """Decorator to parse content from YAML.

    Args:
        strategy: How to handle parsing errors (STRICT or PERMISSIVE)
        handle_non_dict: If True, wrap non-dict values in {"value": ...}

    Example:
        >>> @parse_as_yaml()
        ... class MyContent(BaseContent):
        ...     key: str
        ...     value: int
    """

    def decorator(cls: type[T]) -> type[T]:
        def parse(cls_inner: type[T], raw_text: str) -> T:
            if not raw_text.strip():
                return cls_inner(raw_content=raw_text)

            try:
                loaded_data: dict[str, Any] | str | None = yaml.safe_load(raw_text)
                if isinstance(loaded_data, dict):
                    data: dict[str, Any] = loaded_data
                elif handle_non_dict and loaded_data is not None:
                    data = {"value": loaded_data}
                else:
                    data = {}

                return cls_inner(raw_content=raw_text, **data)

            except yaml.YAMLError:
                if strategy == ParseStrategy.STRICT:
                    raise
                # PERMISSIVE: fall back to raw content
                return cls_inner(raw_content=raw_text)
            except (TypeError, ValidationError):
                # Pydantic validation error
                if strategy == ParseStrategy.STRICT:
                    raise
                return cls_inner(raw_content=raw_text)

        cls.parse = classmethod(parse)  # type: ignore[assignment]
        return cls

    return decorator


def parse_as_json[T: BaseContent](
    *,
    strategy: ParseStrategy = ParseStrategy.PERMISSIVE,
    handle_non_dict: bool = True,
) -> Callable[[type[T]], type[T]]:
    """Decorator to parse content from JSON.

    Args:
        strategy: How to handle parsing errors (STRICT or PERMISSIVE)
        handle_non_dict: If True, wrap non-dict values in {"value": ...}

    Example:
        >>> @parse_as_json()
        ... class MyContent(BaseContent):
        ...     status: int
        ...     data: dict[str, Any]
    """

    def decorator(cls: type[T]) -> type[T]:
        def parse(cls_inner: type[T], raw_text: str) -> T:
            if not raw_text.strip():
                return cls_inner(raw_content=raw_text)

            try:
                loaded_data: dict[str, Any] | str | None = json.loads(raw_text)
                if isinstance(loaded_data, dict):
                    data: dict[str, Any] = loaded_data
                elif handle_non_dict:
                    data = {"value": loaded_data}
                else:
                    data = {}

                return cls_inner(raw_content=raw_text, **data)

            except json.JSONDecodeError:
                if strategy == ParseStrategy.STRICT:
                    raise
                # PERMISSIVE: fall back to raw content
                return cls_inner(raw_content=raw_text)
            except (TypeError, ValidationError):
                # Pydantic validation error
                if strategy == ParseStrategy.STRICT:
                    raise
                return cls_inner(raw_content=raw_text)

        cls.parse = classmethod(parse)  # type: ignore[assignment]
        return cls

    return decorator
