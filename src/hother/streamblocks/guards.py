"""Ready-made stream validators that reject a block while it is still being written.

Register them with :meth:`hother.streamblocks.Registry.add_stream_validator`.
Combined with ``ProcessorConfig(abort_stream_on_failure=True)`` they stop a
model as soon as it starts writing something it should not, instead of paying
for the rest of the output.

Example:
    >>> from hother.streamblocks import Registry, XmlTagSyntax
    >>> from hother.streamblocks.blocks.artifacts import ARTIFACT_BLOCKS
    >>> from hother.streamblocks.guards import path_within
    >>> registry = Registry(syntax=XmlTagSyntax(), blocks=ARTIFACT_BLOCKS)
    >>> registry.add_stream_validator(path_within("src", "tests"))
"""

from __future__ import annotations

import posixpath
import re
from typing import TYPE_CHECKING

from hother.streamblocks.core.registry import ValidationResult
from hother.streamblocks.core.types import SectionType

if TYPE_CHECKING:
    from hother.streamblocks.core.registry import StreamValidatorFunc
    from hother.streamblocks.core.types import PartialBlock

_PARENT_DIRECTORY = ".."
_PATH_SEPARATOR = "/"
_WINDOWS_SEPARATOR = "\\"
_DRIVE_PATTERN = re.compile(r"^[A-Za-z]:")


def path_within(*roots: str, field: str = "path") -> StreamValidatorFunc:
    """Reject a block whose path metadata points outside the allowed directories.

    The check runs as soon as the metadata is known: on the opening line for
    the XML tag and preamble syntaxes, at the end of the frontmatter otherwise.
    Blocks without the field are left alone.

    Args:
        *roots: Allowed directories, relative to the project root. With no
            root, any relative path that stays inside the project is allowed.
        field: Name of the metadata field holding the path
    """
    allowed = tuple(posixpath.normpath(root.replace(_WINDOWS_SEPARATOR, _PATH_SEPARATOR)) for root in roots)

    def validate(partial: PartialBlock) -> ValidationResult:
        value = (partial.metadata or {}).get(field)
        if value is None:
            return ValidationResult.success()

        raw = str(value).replace(_WINDOWS_SEPARATOR, _PATH_SEPARATOR)
        path = posixpath.normpath(raw)
        escapes = path == _PARENT_DIRECTORY or path.startswith(_PARENT_DIRECTORY + _PATH_SEPARATOR)
        if posixpath.isabs(raw) or _DRIVE_PATTERN.match(raw) or escapes:
            return ValidationResult.failure(f"Path {value!r} is outside the project")
        if allowed and not any(path == root or path.startswith(root + _PATH_SEPARATOR) for root in allowed):
            return ValidationResult.failure(f"Path {value!r} is not under {', '.join(allowed)}")
        return ValidationResult.success()

    return validate


def max_lines(limit: int) -> StreamValidatorFunc:
    """Reject a block as soon as its content has more than ``limit`` lines."""

    def validate(partial: PartialBlock) -> ValidationResult:
        if len(partial.content_lines) > limit:
            return ValidationResult.failure(f"Block content exceeds {limit} lines")
        return ValidationResult.success()

    return validate


def max_size(limit: int) -> StreamValidatorFunc:
    """Reject a block as soon as it is larger than ``limit`` characters."""

    def validate(partial: PartialBlock) -> ValidationResult:
        if partial.size > limit:
            return ValidationResult.failure(f"Block exceeds {limit} characters")
        return ValidationResult.success()

    return validate


def forbid_patterns(*patterns: str | re.Pattern[str]) -> StreamValidatorFunc:
    """Reject a block as soon as one of its content lines matches a forbidden pattern.

    Args:
        *patterns: Regular expressions, searched in each new content line
    """
    compiled = tuple(re.compile(pattern) for pattern in patterns)

    def validate(partial: PartialBlock) -> ValidationResult:
        if partial.section != SectionType.CONTENT:
            return ValidationResult.success()
        for pattern in compiled:
            if pattern.search(partial.line):
                return ValidationResult.failure(
                    f"Line {partial.line_number} matches forbidden pattern {pattern.pattern!r}"
                )
        return ValidationResult.success()

    return validate
