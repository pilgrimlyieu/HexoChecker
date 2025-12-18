"""Core module - 核心组件"""

from checks.core.checker import Checker
from checks.core.context import CheckContext
from checks.core.exceptions import (
    CheckerError,
    CheckerNotFoundError,
    ChecksError,
    ConfigError,
    ConfigLoadError,
    ConfigNotFoundError,
    ConfigValidationError,
    FileError,
    FileReadError,
    FileWriteError,
    FixError,
    PatchApplyError,
    PatchError,
    PatchRevertError,
)
from checks.core.issue import ContextLines, Fix, Issue, Severity
from checks.core.resolver import PathResolver

__all__ = [
    "CheckContext",
    # Base classes
    "Checker",
    "CheckerError",
    "CheckerNotFoundError",
    # Exceptions
    "ChecksError",
    "ConfigError",
    "ConfigLoadError",
    "ConfigNotFoundError",
    "ConfigValidationError",
    "ContextLines",
    "FileError",
    "FileReadError",
    "FileWriteError",
    "Fix",
    "FixError",
    # Issue
    "Issue",
    "PatchApplyError",
    "PatchError",
    "PatchRevertError",
    "PathResolver",
    "Severity",
]
