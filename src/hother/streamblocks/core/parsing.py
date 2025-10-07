"""Parsing decorators for content models."""

from __future__ import annotations

import json
from enum import StrEnum
from typing import TYPE_CHECKING, TypeVar

import yaml
from pydantic import ValidationError

if TYPE_CHECKING:
    from collections.abc import Callable

    from pydantic import BaseModel

T = TypeVar("T", bound="BaseModel")


class ParseStrategy(StrEnum):
    """Strategy for handling parsing errors."""

    STRICT = "strict"  # Raise exception on parse error
    PERMISSIVE = "permissive"  # Fall back to raw_content on error


def parse_as_yaml(
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
                data = yaml.safe_load(raw_text) or {}

                # Handle non-dict YAML values
                if handle_non_dict and not isinstance(data, dict):
                    data = {"value": data}

                return cls_inner(raw_content=raw_text, **data)

            except yaml.YAMLError as e:
                if strategy == ParseStrategy.STRICT:
                    msg = f"Invalid YAML: {e}"
                    raise ValueError(msg) from e
                # PERMISSIVE: fall back to raw content
                return cls_inner(raw_content=raw_text)
            except (TypeError, ValidationError) as e:
                # Pydantic validation error
                if strategy == ParseStrategy.STRICT:
                    msg = f"YAML data doesn't match model: {e}"
                    raise ValueError(msg) from e
                return cls_inner(raw_content=raw_text)

        cls.parse = classmethod(parse)
        return cls

    return decorator


def parse_as_json(
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
                data = json.loads(raw_text)

                # Handle non-dict JSON values
                if handle_non_dict and not isinstance(data, dict):
                    data = {"value": data}

                return cls_inner(raw_content=raw_text, **data)

            except json.JSONDecodeError as e:
                if strategy == ParseStrategy.STRICT:
                    msg = f"Invalid JSON: {e}"
                    raise ValueError(msg) from e
                # PERMISSIVE: fall back to raw content
                return cls_inner(raw_content=raw_text)
            except (TypeError, ValidationError) as e:
                # Pydantic validation error
                if strategy == ParseStrategy.STRICT:
                    msg = f"JSON data doesn't match model: {e}"
                    raise ValueError(msg) from e
                return cls_inner(raw_content=raw_text)

        cls.parse = classmethod(parse)
        return cls

    return decorator
