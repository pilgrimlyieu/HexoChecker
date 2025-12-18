"""Config - 配置系统"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from checks.core.checker import Checker
    from checks.core.resolver import PathResolver
    from checks.reporters.base import Reporter


@dataclass
class OutputConfig:
    """输出配置"""

    context_lines: int = 3
    show_suggestions: bool = True
    color: str = "auto"  # auto | always | never


@dataclass
class FixConfig:
    """修复配置"""

    patch_dir: str = ".checks/patches"
    auto_backup: bool = True
    dry_run: bool = False


@dataclass
class Config:
    """主配置类

    Attributes:
        root: 项目根目录（相对于配置文件位置）
        include: 要检查的文件 glob 模式
        exclude: 要排除的文件 glob 模式
        resolver: 路径解析器
        checkers: 检查器列表
        reporter: 报告器
        output: 输出配置
        fix: 修复配置
    """

    root: str | Path = "."
    include: list[str] = field(default_factory=lambda: ["**/*.md"])
    exclude: list[str] = field(default_factory=list)

    # 组件（延迟初始化）
    resolver: PathResolver | None = None
    checkers: list[Checker] = field(default_factory=list)
    reporter: Reporter | None = None

    # 子配置
    output: OutputConfig = field(default_factory=OutputConfig)
    fix: FixConfig = field(default_factory=FixConfig)

    # 钩子函数
    before_check: Callable[..., Any] | None = None
    after_check: Callable[..., Any] | None = None
    before_fix: Callable[..., Any] | None = None
    after_fix: Callable[..., Any] | None = None

    def __post_init__(self):
        """初始化默认组件"""
        self.root = Path(self.root)

        # 默认解析器
        if self.resolver is None:
            from checks.resolvers.default import DefaultResolver

            self.resolver = DefaultResolver()

        # 默认检查器
        if not self.checkers:
            from checks.checkers.image import ImageChecker

            self.checkers = [ImageChecker()]

        # 默认报告器
        if self.reporter is None:
            from checks.reporters.console import ColorMode, ConsoleReporter

            color_mode = ColorMode(self.output.color)
            self.reporter = ConsoleReporter(
                context_lines=self.output.context_lines,
                show_suggestions=self.output.show_suggestions,
                color=color_mode,
            )

    def resolve_root(self, config_dir: Path) -> Path:
        """解析项目根目录的绝对路径

        Args:
            config_dir: 配置文件所在目录

        Returns:
            项目根目录的绝对路径
        """
        # __post_init__ 已将 root 转换为 Path
        root = self.root if isinstance(self.root, Path) else Path(self.root)
        if root.is_absolute():
            return root
        return (config_dir / root).resolve()


def load_config(config_path: Path | str | None = None) -> tuple[Config, Path]:
    """加载配置文件

    查找顺序：
    1. 指定的配置文件路径
    2. 当前目录的 checks_config.py
    3. 向上递归查找 checks_config.py

    Args:
        config_path: 配置文件路径（可选）

    Returns:
        (配置对象, 配置文件所在目录)

    Raises:
        FileNotFoundError: 找不到配置文件
        ImportError: 配置文件加载失败
    """
    import importlib.util
    import sys

    # 查找配置文件
    if config_path:
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
    else:
        config_file = _find_config_file()
        if not config_file:
            # 没有找到配置文件，使用默认配置
            return Config(), Path.cwd()

    config_file = config_file.resolve()
    config_dir = config_file.parent

    # 动态导入配置模块
    spec = importlib.util.spec_from_file_location("checks_config", config_file)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load config file: {config_file}")

    module = importlib.util.module_from_spec(spec)
    sys.modules["checks_config"] = module

    try:
        spec.loader.exec_module(module)
    except Exception as e:
        raise ImportError(f"Error loading config file: {e}") from e

    # 获取 config 对象
    if not hasattr(module, "config"):
        raise ImportError("Config file must define a 'config' variable")

    config = module.config
    if not isinstance(config, Config):
        raise ImportError("'config' must be an instance of Config")

    return config, config_dir


def _find_config_file() -> Path | None:
    """向上递归查找配置文件"""
    current = Path.cwd()

    while True:
        config_file = current / "checks_config.py"
        if config_file.exists():
            return config_file

        parent = current.parent
        if parent == current:
            # 已到达根目录
            return None
        current = parent
