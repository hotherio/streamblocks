"""Prompt generation from block registries and block classes."""

from hother.streamblocks.prompts.builder import generate_block_prompt
from hother.streamblocks.prompts.manager import TemplateManager

__all__ = [
    "TemplateManager",
    "generate_block_prompt",
]
