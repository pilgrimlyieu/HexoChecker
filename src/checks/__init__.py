"""
Checks Framework - 可扩展的博客内容检查框架

支持图片路径验证、链接检查等多种检查类型，
提供插件化架构、Python 配置、交互式修复。
"""

from checks.checkers import ImageChecker
from checks.config import Config, FixConfig, OutputConfig
from checks.core.checker import Checker
from checks.core.context import CheckContext
from checks.core.exceptions import (
    CheckerError,
    ChecksError,
    ConfigError,
    FileError,
    FixError,
    PatchError,
)
from checks.core.issue import ContextLines, Fix, Issue, Severity
from checks.core.resolver import PathResolver
from checks.resolvers import DefaultResolver, HexoResolver
from checks.runner import CheckRunner

__all__ = [
    "CheckContext",
    # Runner
    "CheckRunner",
    "Checker",
    "CheckerError",
    # Exceptions
    "ChecksError",
    # Config
    "Config",
    "ConfigError",
    "ContextLines",
    # Resolvers
    "DefaultResolver",
    "FileError",
    "Fix",
    "FixConfig",
    "FixError",
    "HexoResolver",
    # Checkers
    "ImageChecker",
    # Core
    "Issue",
    "OutputConfig",
    "PatchError",
    "PathResolver",
    "Severity",
]

__version__ = "0.1.0"
