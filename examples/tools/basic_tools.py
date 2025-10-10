"""Basic tools for demonstration."""

import json
import os
import random
from datetime import datetime
from pathlib import Path
from typing import Any


class BasicTools:
    """Collection of basic tools for demonstrations."""

    # Calculator Tools
    @staticmethod
    def calculate(expression: str) -> float:
        """Safely evaluate a mathematical expression."""
        # Remove any potentially dangerous characters
        allowed_chars = "0123456789+-*/.() "
        cleaned = "".join(c for c in expression if c in allowed_chars)

        try:
            # Use eval with restricted namespace
            result = eval(cleaned, {"__builtins__": {}}, {})
            return float(result)
        except Exception as e:
            msg = f"Invalid expression: {e}"
            raise ValueError(msg)

    @staticmethod
    def add(a: float, b: float) -> float:
        """Add two numbers."""
        return a + b

    @staticmethod
    def multiply(a: float, b: float) -> float:
        """Multiply two numbers."""
        return a * b

    @staticmethod
    def divide(a: float, b: float) -> float:
        """Divide two numbers with zero check."""
        if b == 0:
            msg = "Division by zero"
            raise ValueError(msg)
        return a / b

    # String Tools
    @staticmethod
    def uppercase(text: str) -> str:
        """Convert text to uppercase."""
        return text.upper()

    @staticmethod
    def lowercase(text: str) -> str:
        """Convert text to lowercase."""
        return text.lower()

    @staticmethod
    def reverse(text: str) -> str:
        """Reverse a string."""
        return text[::-1]

    @staticmethod
    def word_count(text: str) -> dict[str, int]:
        """Count words in text."""
        words = text.split()
        return {
            "total_words": len(words),
            "unique_words": len(set(words)),
            "character_count": len(text),
            "line_count": len(text.splitlines()),
        }

    # System Tools
    @staticmethod
    def get_time(format: str = "%H:%M:%S") -> str:
        """Get current time."""
        return datetime.now().strftime(format)

    @staticmethod
    def get_date(format: str = "%Y-%m-%d") -> str:
        """Get current date."""
        return datetime.now().strftime(format)

    @staticmethod
    def random_number(min_val: int = 0, max_val: int = 100) -> int:
        """Generate a random number."""
        return random.randint(min_val, max_val)

    # File Tools
    @staticmethod
    def read_file(path: str, max_lines: int = 100) -> str:
        """Read a file's content."""
        try:
            with open(path, encoding="utf-8") as f:
                lines = f.readlines()[:max_lines]
                content = "".join(lines)
                if len(lines) == max_lines:
                    content += f"\n... (truncated at {max_lines} lines)"
                return content
        except Exception as e:
            return f"Error reading file: {e}"

    @staticmethod
    def list_files(directory: str = ".", pattern: str = "*") -> list[str]:
        """List files in a directory."""
        try:
            path = Path(directory)
            files = [str(f.relative_to(path)) for f in path.glob(pattern) if f.is_file()]
            return sorted(files)
        except Exception as e:
            return [f"Error: {e}"]

    # Utility Tools
    @staticmethod
    def format_json(data: Any, indent: int = 2) -> str:
        """Format data as pretty JSON."""
        return json.dumps(data, indent=indent, ensure_ascii=False)

    @staticmethod
    def get_environment_variable(name: str, default: str | None = None) -> str | None:
        """Get an environment variable."""
        return os.environ.get(name, default)
