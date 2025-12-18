"""Fixers module - 修复器实现"""

from checks.fixers.base import Fixer, FixResult
from checks.fixers.interactive import InteractiveFixer
from checks.fixers.patch import PatchFixer

__all__ = [
    "FixResult",
    "Fixer",
    "InteractiveFixer",
    "PatchFixer",
]
