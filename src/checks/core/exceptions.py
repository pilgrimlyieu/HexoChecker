"""Exceptions - 自定义异常类"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path


class ChecksError(Exception):
    """Checks 框架基础异常类"""

    def __init__(self, message: str, **context: Any) -> None:
        super().__init__(message)
        self.message = message
        self.context = context

    def __str__(self) -> str:
        if self.context:
            ctx_str = ", ".join(f"{k}={v!r}" for k, v in self.context.items())
            return f"{self.message} ({ctx_str})"
        return self.message


class ConfigError(ChecksError):
    """配置相关错误"""


class ConfigNotFoundError(ConfigError):
    """配置文件未找到"""

    def __init__(self, search_paths: list[Path] | None = None) -> None:
        message = "Configuration file not found"
        super().__init__(message, search_paths=search_paths)
        self.search_paths = search_paths


class ConfigLoadError(ConfigError):
    """配置文件加载失败"""

    def __init__(self, path: Path, reason: str) -> None:
        message = f"Failed to load config file: {reason}"
        super().__init__(message, path=path, reason=reason)
        self.path = path
        self.reason = reason


class ConfigValidationError(ConfigError):
    """配置验证失败"""

    def __init__(self, field: str, value: Any, expected: str) -> None:
        type_name = type(value).__name__
        message = f"Invalid config value for '{field}': expected {expected}, got {type_name}"
        super().__init__(message, field=field, value=value, expected=expected)
        self.field = field
        self.value = value
        self.expected = expected


class CheckerError(ChecksError):
    """检查器相关错误"""


class CheckerNotFoundError(CheckerError):
    """检查器未找到"""

    def __init__(self, name: str, available: list[str] | None = None) -> None:
        message = f"Checker not found: {name}"
        super().__init__(message, name=name, available=available)
        self.name = name
        self.available = available


class FileError(ChecksError):
    """文件操作相关错误"""


class FileReadError(FileError):
    """文件读取失败"""

    def __init__(self, path: Path, reason: str) -> None:
        message = f"Failed to read file: {reason}"
        super().__init__(message, path=path, reason=reason)
        self.path = path
        self.reason = reason


class FileWriteError(FileError):
    """文件写入失败"""

    def __init__(self, path: Path, reason: str) -> None:
        message = f"Failed to write file: {reason}"
        super().__init__(message, path=path, reason=reason)
        self.path = path
        self.reason = reason


class FixError(ChecksError):
    """修复相关错误"""


class PatchError(FixError):
    """Patch 操作失败"""

    def __init__(self, path: Path, reason: str) -> None:
        message = f"Patch operation failed: {reason}"
        super().__init__(message, path=path, reason=reason)
        self.path = path
        self.reason = reason


class PatchApplyError(PatchError):
    """Patch 应用失败"""


class PatchRevertError(PatchError):
    """Patch 撤销失败"""
