"""Code snippet extraction and injection for MkDocs.

This module provides functionality to extract specific sections from Python files
using markers like ### [section_name] and embed them in documentation.
"""

import re
import sys
from dataclasses import dataclass
from pathlib import Path

# Add hooks directory to path for imports
_hooks_dir = Path(__file__).parent
if str(_hooks_dir) not in sys.path:
    sys.path.insert(0, str(_hooks_dir))

import utils


@dataclass
class CodeSection:
    """Represents a code section extracted from a file."""

    name: str
    lines: list[str]
    start_line: int
    end_line: int

    @property
    def code(self) -> str:
        """Get the code content as a string."""
        return "\n".join(self.lines)


class SectionExtractor:
    """Extract named sections from Python files using markers.

    Supported marker styles:
    - Pydantic-AI style: ### [section_name]
    - End marker: ### [/section_name] (optional - can use next section as end)

    Example:
        ### [setup]
        from hother.streamblocks import StreamBlockProcessor
        logger = get_logger(__name__)
        ### [/setup]

        ### [example]
        async def main():
            async with StreamBlockProcessor() as processor:
                await processor.process_stream(stream)
        ### [/example]
    """

    # Pattern for section start: ### [section_name]
    START_PATTERN = re.compile(r"^\s*###\s*\[(\w+)\]\s*$")

    # Pattern for section end: ### [/section_name]
    END_PATTERN = re.compile(r"^\s*###\s*\[/(\w+)\]\s*$")

    def __init__(self, file_path: Path) -> None:
        """Initialize extractor for a specific file.

        Args:
            file_path: Path to the Python file to extract from
        """
        self.file_path = file_path
        self.lines = file_path.read_text().splitlines()
        self._sections: dict[str, list[CodeSection]] | None = None

    @property
    def sections(self) -> dict[str, list[CodeSection]]:
        """Get all sections from the file (cached).

        Returns:
            Dictionary mapping section names to list of CodeSection objects
        """
        if self._sections is None:
            self._sections = self._parse_sections()
        return self._sections

    def _parse_sections(self) -> dict[str, list[CodeSection]]:
        """Parse the file and extract all marked sections.

        Returns:
            Dictionary of section name -> list of CodeSection objects
        """
        sections: dict[str, list[CodeSection]] = {}
        active_sections: list[tuple[str, int, list[str]]] = []

        for line_num, line in enumerate(self.lines, start=1):
            # Check for section start marker
            start_match = self.START_PATTERN.match(line)
            if start_match:
                section_name = start_match.group(1)
                # Start tracking this section
                active_sections.append((section_name, line_num + 1, []))
                continue

            # Check for section end marker
            end_match = self.END_PATTERN.match(line)
            if end_match:
                section_name = end_match.group(1)
                # Find and close the matching active section
                for i, (active_name, start_line, collected_lines) in enumerate(active_sections):
                    if active_name == section_name:
                        # Create section object
                        section = CodeSection(
                            name=section_name,
                            lines=collected_lines,
                            start_line=start_line,
                            end_line=line_num - 1,
                        )

                        # Add to sections dict
                        if section_name not in sections:
                            sections[section_name] = []
                        sections[section_name].append(section)

                        # Remove from active sections
                        active_sections.pop(i)
                        break
                continue

            # Add line to all active sections
            for _, _, collected_lines in active_sections:
                collected_lines.append(line)

        # Handle unclosed sections (treat end of file as implicit end)
        for section_name, start_line, collected_lines in active_sections:
            section = CodeSection(
                name=section_name,
                lines=collected_lines,
                start_line=start_line,
                end_line=len(self.lines),
            )

            if section_name not in sections:
                sections[section_name] = []
            sections[section_name].append(section)

        return sections

    def get_section(self, name: str) -> CodeSection | None:
        """Get a specific section by name.

        Args:
            name: Name of the section to retrieve

        Returns:
            CodeSection object if found, None otherwise
            If multiple sections with same name exist, returns the first one
        """
        section_list = self.sections.get(name)
        if section_list:
            return section_list[0]
        return None

    def get_all_sections(self, name: str) -> list[CodeSection]:
        """Get all sections with the given name.

        Args:
            name: Name of the sections to retrieve

        Returns:
            List of CodeSection objects (may be empty)
        """
        return self.sections.get(name, [])

    def merge_sections(self, names: list[str]) -> str | None:
        """Merge multiple sections into a single code block.

        Args:
            names: List of section names to merge

        Returns:
            Merged code as a string with ellipsis between sections,
            or None if any section is not found
        """
        merged_lines: list[str] = []

        for i, name in enumerate(names):
            section = self.get_section(name)
            if section is None:
                return None

            # Add ellipsis between sections (but not before first)
            if i > 0:
                merged_lines.append("...")
                merged_lines.append("")

            merged_lines.extend(section.lines)

        return "\n".join(merged_lines)


def process_snippet_directive(
    file_path: str,
    section: str | None = None,
    sections: list[str] | None = None,
) -> str:
    """Process a snippet directive and return formatted code block.

    Args:
        file_path: Path to the source file
        section: Optional single section name to extract
        sections: Optional list of section names to merge

    Returns:
        Formatted markdown code block with GitHub link,
        or error message if file/section not found
    """
    # Resolve file path
    resolved_path = utils.resolve_file_path(file_path)
    if resolved_path is None:
        return f'!!! error "Snippet file not found"\n    Could not find: `{file_path}`'

    try:
        # If no section specified, return full file content
        if section is None and sections is None:
            code = resolved_path.read_text()
            return utils.format_code_block(code, file_path)

        # Extract sections
        extractor = SectionExtractor(resolved_path)

        # Handle single section
        if section:
            section_obj = extractor.get_section(section)
            if section_obj is None:
                available = ", ".join(extractor.sections.keys())
                return (
                    f'!!! error "Section not found"\n'
                    f"    Section `{section}` not found in `{file_path}`\n\n"
                    f"    Available sections: {available or 'none'}"
                )

            return utils.format_code_block(
                section_obj.code,
                file_path,
                start_line=section_obj.start_line,
                end_line=section_obj.end_line,
            )

        # Handle multiple sections
        if sections:
            merged_code = extractor.merge_sections(sections)
            if merged_code is None:
                available = ", ".join(extractor.sections.keys())
                return (
                    f'!!! error "One or more sections not found"\n'
                    f"    Could not find all requested sections in `{file_path}`\n\n"
                    f"    Requested: {', '.join(sections)}\n\n"
                    f"    Available: {available or 'none'}"
                )

            # For merged sections, don't include line numbers
            return utils.format_code_block(merged_code, file_path)

    except Exception as e:
        return f'!!! error "Failed to process snippet"\n    Error: {e}'

    return ""


def inject_snippets(markdown: str) -> str:
    """Replace snippet directives with actual code blocks.

    Supported syntax:
        ```snippet path="examples/file.py"```
        ```snippet path="examples/file.py" section="setup"```
        ```snippet path="examples/file.py" sections="setup,example"```

    Args:
        markdown: Markdown content to process

    Returns:
        Markdown with snippet directives replaced
    """
    # Pattern for snippet code blocks with attributes
    pattern = r'```snippet\s+path="([^"]+)"(?:\s+section="([^"]+)")?(?:\s+sections="([^"]+)")?\s*```'

    def replace_snippet(match: re.Match[str]) -> str:
        """Replace a single snippet directive."""
        file_path = match.group(1)
        section = match.group(2)
        sections_str = match.group(3)

        # Parse sections list if provided
        sections_list = None
        if sections_str:
            sections_list = [s.strip() for s in sections_str.split(",")]

        return process_snippet_directive(file_path, section, sections_list)

    # Replace all snippet directives
    return re.sub(pattern, replace_snippet, markdown)
