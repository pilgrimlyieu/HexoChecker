"""CheckRunner - 检查运行器"""

from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path
from typing import TYPE_CHECKING

from checks.core.context import CheckContext

if TYPE_CHECKING:
    from checks.config import Config
    from checks.core.issue import Issue


@dataclass
class CheckRunner:
    """检查运行器

    协调检查器、解析器、报告器完成检查流程。

    Attributes:
        config: 配置对象
        root: 项目根目录
    """

    config: Config
    root: Path

    _context: CheckContext = field(init=False, repr=False)

    def __post_init__(self):
        """初始化检查上下文"""
        self.root = Path(self.root).resolve()
        # resolver 在 Config.__post_init__ 中已确保非 None
        assert self.config.resolver is not None, "Config.resolver must be set"
        self._context = CheckContext(
            root=self.root,
            config=self.config,
            resolver=self.config.resolver,
        )

    def run(self, report: bool = True) -> list[Issue]:
        """运行检查

        Args:
            report: 是否输出报告

        Returns:
            发现的问题列表
        """
        # 前置钩子
        if self.config.before_check:
            self.config.before_check(self._context)

        # 收集要检查的文件
        files = self._collect_files()

        # 运行检查
        all_issues: list[Issue] = []
        for file in files:
            issues = self._check_file(file)
            all_issues.extend(issues)

        # 填充上下文信息
        for issue in all_issues:
            if issue.context is None:
                issue.context = self._context.get_context_lines(
                    issue.file,
                    issue.line,
                    before=self.config.output.context_lines,
                    after=self.config.output.context_lines,
                )

        # 后置钩子
        if self.config.after_check:
            self.config.after_check(self._context, all_issues)

        # 输出报告
        if report and self.config.reporter:
            self.config.reporter.report(all_issues, self.root)

        return all_issues

    def _collect_files(self) -> list[Path]:
        """收集要检查的文件"""
        files: list[Path] = []

        for pattern in self.config.include:
            for file in self.root.glob(pattern):
                if file.is_file() and not self._is_excluded(file):
                    files.append(file)

        return sorted(set(files))

    def _is_excluded(self, file: Path) -> bool:
        """检查文件是否被排除"""
        try:
            rel_path = file.relative_to(self.root)
        except ValueError:
            return True

        rel_str = rel_path.as_posix()

        return any(fnmatch(rel_str, pattern) for pattern in self.config.exclude)

    def _check_file(self, file: Path) -> list[Issue]:
        """检查单个文件"""
        issues: list[Issue] = []

        # 读取文件内容
        try:
            content = self._context.read_file(file)
        except Exception:
            # 文件读取失败，跳过
            return issues

        # 运行每个检查器
        for checker in self.config.checkers:
            if not checker.enabled:
                continue
            if not checker.supports_file(file):
                continue

            try:
                checker_issues = checker.check(file, content, self._context)
                issues.extend(checker_issues)
            except Exception:
                # 检查器错误，跳过
                pass

        return issues

    @property
    def context(self) -> CheckContext:
        """获取检查上下文"""
        return self._context


def run_checks(
    config: Config | None = None, root: Path | str | None = None, report: bool = True
) -> list[Issue]:
    """便捷函数：运行检查

    Args:
        config: 配置对象（None 则加载默认配置）
        root: 项目根目录（None 则从配置确定）
        report: 是否输出报告

    Returns:
        发现的问题列表
    """
    from checks.config import load_config

    if config is None:
        config, config_dir = load_config()
        if root is None:
            root = config.resolve_root(config_dir)

    root = Path.cwd() if root is None else Path(root) if isinstance(root, str) else root

    runner = CheckRunner(config=config, root=root)
    return runner.run(report=report)
