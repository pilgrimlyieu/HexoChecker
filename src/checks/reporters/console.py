"""ConsoleReporter - 终端彩色输出报告器"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from checks.core.issue import Issue, Severity
from checks.reporters.base import Reporter

if TYPE_CHECKING:
    from pathlib import Path


class ColorMode(Enum):
    """颜色模式"""

    AUTO = "auto"
    ALWAYS = "always"
    NEVER = "never"


@dataclass
class Theme:
    """颜色主题"""

    # 文件和位置
    file: str = "96"  # 青色
    line_num: str = "93"  # 黄色

    # 严重程度
    error: str = "91"  # 红色
    warning: str = "93"  # 黄色
    info: str = "94"  # 蓝色

    # 内容
    original: str = "91"  # 红色（错误内容）
    suggestion: str = "92"  # 绿色（建议内容）
    context: str = "90"  # 灰色（上下文）

    # 装饰
    border: str = "90"  # 灰色（边框）
    highlight: str = "95"  # 品红（高亮）

    # 默认主题
    @classmethod
    def default(cls) -> Theme:
        return cls()

    @classmethod
    def light(cls) -> Theme:
        """浅色终端主题"""
        return cls(
            file="36",  # 深青
            line_num="33",  # 棕色
            error="31",  # 深红
            warning="33",  # 棕色
            info="34",  # 深蓝
            original="31",
            suggestion="32",
            context="37",  # 浅灰
            border="37",
            highlight="35",
        )


@dataclass
class ConsoleReporter(Reporter):
    """终端彩色输出报告器

    类似 delta/git diff 风格的输出，支持：
    - 彩色高亮
    - 上下文行显示
    - 建议修复展示
    - 行号和列号标记

    Attributes:
        context_lines: 显示的上下文行数
        show_suggestions: 是否显示修复建议
        color: 颜色模式
        theme: 颜色主题
        line_numbers: 是否显示行号
        box_drawing: 是否使用 Unicode 框线字符
    """

    name: str = "console"
    description: str = "Console reporter with color output"

    context_lines: int = 3
    show_suggestions: bool = True
    color: ColorMode = ColorMode.AUTO
    theme: Theme = field(default_factory=Theme.default)
    line_numbers: bool = True
    box_drawing: bool = True

    # 框线字符
    _box_chars: dict = field(
        default_factory=lambda: {
            "top_left": "╭",
            "top_right": "╮",
            "bottom_left": "╰",
            "bottom_right": "╯",
            "vertical": "│",
            "horizontal": "─",
            "tee_right": "├",
            "tee_left": "┤",
        },
        repr=False,
    )

    _simple_chars: dict = field(
        default_factory=lambda: {
            "top_left": "+",
            "top_right": "+",
            "bottom_left": "+",
            "bottom_right": "+",
            "vertical": "|",
            "horizontal": "-",
            "tee_right": "+",
            "tee_left": "+",
        },
        repr=False,
    )

    def __post_init__(self):
        """初始化颜色支持检测"""
        self._use_color = self._should_use_color()
        self._chars = self._box_chars if self.box_drawing else self._simple_chars

    def _should_use_color(self) -> bool:
        """判断是否应该使用颜色"""
        if self.color == ColorMode.ALWAYS:
            return True
        if self.color == ColorMode.NEVER:
            return False
        # AUTO: 检查是否为 TTY
        return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

    def _style(self, text: str, code: str) -> str:
        """应用 ANSI 样式"""
        if not self._use_color:
            return text
        return f"\033[{code}m{text}\033[0m"

    def _severity_color(self, severity: Severity) -> str:
        """获取严重程度对应的颜色代码"""
        match severity:
            case Severity.ERROR:
                return self.theme.error
            case Severity.WARNING:
                return self.theme.warning
            case Severity.INFO:
                return self.theme.info

    def report(self, issues: list[Issue], root: Path) -> None:
        """输出所有问题"""
        if not issues:
            print(self._style("✓ No issues found", "92"))
            return

        # 按文件分组
        by_file: dict[Path, list[Issue]] = {}
        for issue in issues:
            by_file.setdefault(issue.file, []).append(issue)

        # 输出每个文件的问题
        for file, file_issues in by_file.items():
            self._report_file(file, file_issues, root)

        # 输出摘要
        self.report_summary(issues)

    def _report_file(self, file: Path, issues: list[Issue], root: Path) -> None:
        """输出单个文件的所有问题"""
        # 按行号排序
        issues = sorted(issues, key=lambda i: i.line)

        # 文件头
        try:
            rel_path = file.relative_to(root)
        except ValueError:
            rel_path = file

        print()
        print(
            f"{self._chars['top_left']}{self._chars['horizontal']} "
            + self._style(rel_path.as_posix(), self.theme.file)
        )
        print(self._chars["vertical"])

        # 输出每个问题
        for issue in issues:
            self._print_issue_block(issue)

        print(self._chars["bottom_left"] + self._chars["horizontal"] * 2)

    def report_issue(self, issue: Issue, root: Path) -> None:
        """输出单个问题（独立显示）"""
        try:
            rel_path = issue.file.relative_to(root)
        except ValueError:
            rel_path = issue.file

        print()
        print(
            f"{self._chars['top_left']}{self._chars['horizontal']} "
            + self._style(rel_path.as_posix(), self.theme.file)
            + self._style(f":{issue.line}", self.theme.line_num)
        )
        print(self._chars["vertical"])
        self._print_issue_block(issue)
        print(self._chars["bottom_left"] + self._chars["horizontal"] * 2)

    def _print_issue_block(self, issue: Issue) -> None:
        """打印问题块（含上下文）"""
        v = self._chars["vertical"]

        if issue.context:
            # 打印上下文前的行
            for line_num, content in issue.context.before:
                self._print_context_line(line_num, content)

            # 打印问题行
            line_num, content = issue.context.current
            self._print_issue_line(line_num, content, issue)

            # 打印上下文后的行
            for line_num, content in issue.context.after:
                self._print_context_line(line_num, content)
        else:
            # 没有上下文，只打印问题信息
            self._print_issue_line(issue.line, issue.original, issue)

        print(v)

    def _print_context_line(self, line_num: int, content: str) -> None:
        """打印上下文行"""
        v = self._chars["vertical"]
        num_str = self._style(f"{line_num:>4}", self.theme.context)
        content_str = self._style(content, self.theme.context)
        print(f"{v}  {num_str} {v} {content_str}")

    def _print_issue_line(self, line_num: int, content: str, issue: Issue) -> None:
        """打印问题行及其标记"""
        v = self._chars["vertical"]

        # 行内容
        num_str = self._style(f"{line_num:>4}", self.theme.line_num)
        print(f"{v}  {num_str} {v} {content}")

        # 下划线标记
        if issue.column is not None and issue.original:
            # 计算下划线位置
            padding = " " * (issue.column)
            underline = "^" * len(issue.original)
            print(f"{v}       {v} {padding}{self._style(underline, self.theme.error)}")

        # 错误消息
        severity_icon = self._get_severity_icon(issue.severity)
        msg = f"{severity_icon} {issue.message}"
        print(f"{v}       {v} {self._style(msg, self._severity_color(issue.severity))}")

        # 建议
        if self.show_suggestions and issue.suggestion:
            suggestion_msg = f"→ Did you mean: `{issue.suggestion}`"
            print(f"{v}       {v} {self._style(suggestion_msg, self.theme.suggestion)}")

    def _get_severity_icon(self, severity: Severity) -> str:
        """获取严重程度图标"""
        match severity:
            case Severity.ERROR:
                return "✗"
            case Severity.WARNING:
                return "⚠"
            case Severity.INFO:
                return "ℹ"

    def report_summary(self, issues: list[Issue]) -> None:
        """输出摘要"""
        if not issues:
            return

        # 统计
        errors = sum(1 for i in issues if i.severity == Severity.ERROR)
        warnings = sum(1 for i in issues if i.severity == Severity.WARNING)
        infos = sum(1 for i in issues if i.severity == Severity.INFO)
        fixable = sum(1 for i in issues if i.has_suggestion)

        # 输出
        print()
        parts = []
        if errors:
            parts.append(self._style(f"{errors} error(s)", self.theme.error))
        if warnings:
            parts.append(self._style(f"{warnings} warning(s)", self.theme.warning))
        if infos:
            parts.append(self._style(f"{infos} info(s)", self.theme.info))

        summary = ", ".join(parts)
        print(f"Found {summary}")

        if fixable:
            print(self._style(f"  {fixable} issue(s) can be auto-fixed", self.theme.suggestion))
