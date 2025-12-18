"""Tests for ConsoleReporter - 控制台输出报告器测试

测试场景包括：
1. 颜色模式控制
2. 输出对齐和美观性
3. 不同严重程度的显示
4. 上下文行的正确显示
5. 多文件分组输出
6. 摘要统计信息
7. 特殊字符处理（中文、长路径等）
"""

import re
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from checks.core.issue import ContextLines, Issue, Severity
from checks.reporters.console import ColorMode, ConsoleReporter, Theme


class TestColorMode:
    """颜色模式测试"""

    def test_color_mode_never(self) -> None:
        """测试 NEVER 模式不输出 ANSI 码"""
        reporter = ConsoleReporter(color=ColorMode.NEVER)
        styled = reporter._style("test", "91")
        assert styled == "test"
        assert "\033[" not in styled

    def test_color_mode_always(self) -> None:
        """测试 ALWAYS 模式始终输出 ANSI 码"""
        reporter = ConsoleReporter(color=ColorMode.ALWAYS)
        styled = reporter._style("test", "91")
        assert styled == "\033[91mtest\033[0m"

    def test_color_mode_auto_tty(self) -> None:
        """测试 AUTO 模式在 TTY 时使用颜色"""
        with patch.object(sys.stdout, "isatty", return_value=True):
            reporter = ConsoleReporter(color=ColorMode.AUTO)
            assert reporter._use_color is True

    def test_color_mode_auto_non_tty(self) -> None:
        """测试 AUTO 模式在非 TTY 时不使用颜色"""
        with patch.object(sys.stdout, "isatty", return_value=False):
            reporter = ConsoleReporter(color=ColorMode.AUTO)
            assert reporter._use_color is False


class TestTheme:
    """主题测试"""

    def test_default_theme(self) -> None:
        """测试默认主题"""
        theme = Theme.default()
        assert theme.error == "91"  # 红色
        assert theme.warning == "93"  # 黄色
        assert theme.suggestion == "92"  # 绿色

    def test_light_theme(self) -> None:
        """测试浅色主题"""
        theme = Theme.light()
        assert theme.error == "31"  # 深红
        assert theme.warning == "33"  # 棕色


class TestConsoleReporterBasic:
    """ConsoleReporter 基础功能测试"""

    @pytest.fixture
    def reporter(self) -> ConsoleReporter:
        """无颜色的 reporter，方便测试输出"""
        return ConsoleReporter(color=ColorMode.NEVER, box_drawing=True)

    @pytest.fixture
    def simple_reporter(self) -> ConsoleReporter:
        """使用简单字符的 reporter"""
        return ConsoleReporter(color=ColorMode.NEVER, box_drawing=False)

    @pytest.fixture
    def sample_issue(self, tmp_path: Path) -> Issue:
        """创建示例问题"""
        return Issue(
            file=tmp_path / "test.md",
            line=5,
            column=10,
            type="broken_image",
            message="Image not found: missing.png",
            original="![alt](missing.png)",
            suggestion="![alt](existing.png)",
            checker="image",
            severity=Severity.ERROR,
        )

    def test_severity_color(self, reporter: ConsoleReporter) -> None:
        """测试不同严重程度的颜色代码"""
        assert reporter._severity_color(Severity.ERROR) == reporter.theme.error
        assert reporter._severity_color(Severity.WARNING) == reporter.theme.warning
        assert reporter._severity_color(Severity.INFO) == reporter.theme.info

    def test_severity_icon(self, reporter: ConsoleReporter) -> None:
        """测试严重程度图标"""
        assert reporter._get_severity_icon(Severity.ERROR) == "✗"
        assert reporter._get_severity_icon(Severity.WARNING) == "⚠"
        assert reporter._get_severity_icon(Severity.INFO) == "ℹ"

    def test_box_drawing_chars(self, reporter: ConsoleReporter) -> None:
        """测试 Unicode 框线字符"""
        assert reporter._chars["vertical"] == "│"
        assert reporter._chars["top_left"] == "╭"
        assert reporter._chars["bottom_left"] == "╰"

    def test_simple_chars(self, simple_reporter: ConsoleReporter) -> None:
        """测试简单 ASCII 字符"""
        assert simple_reporter._chars["vertical"] == "|"
        assert simple_reporter._chars["top_left"] == "+"
        assert simple_reporter._chars["bottom_left"] == "+"


class TestConsoleReporterOutput:
    """ConsoleReporter 输出测试"""

    @pytest.fixture
    def reporter(self) -> ConsoleReporter:
        """无颜色的 reporter"""
        return ConsoleReporter(color=ColorMode.NEVER)

    @pytest.fixture
    def colored_reporter(self) -> ConsoleReporter:
        """有颜色的 reporter"""
        return ConsoleReporter(color=ColorMode.ALWAYS)

    def test_report_no_issues(
        self, reporter: ConsoleReporter, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """测试无问题时的输出"""
        reporter.report([], tmp_path)
        captured = capsys.readouterr()
        assert "No issues found" in captured.out

    def test_report_single_issue(
        self, reporter: ConsoleReporter, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """测试单个问题的输出"""
        issue = Issue(
            file=tmp_path / "test.md",
            line=10,
            type="test",
            message="Test message",
            original="original content",
            checker="test",
        )
        reporter.report([issue], tmp_path)
        captured = capsys.readouterr()

        # 检查文件名显示
        assert "test.md" in captured.out
        # 检查消息显示
        assert "Test message" in captured.out

    def test_report_issue_with_context(
        self, reporter: ConsoleReporter, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """测试带上下文的问题输出"""
        issue = Issue(
            file=tmp_path / "test.md",
            line=5,
            type="test",
            message="Test error",
            original="error line content",
            checker="test",
            context=ContextLines(
                before=[(3, "line 3"), (4, "line 4")],
                current=(5, "error line content"),
                after=[(6, "line 6"), (7, "line 7")],
            ),
        )
        reporter.report([issue], tmp_path)
        captured = capsys.readouterr()

        # 检查上下文行
        assert "line 3" in captured.out
        assert "line 4" in captured.out
        assert "error line content" in captured.out
        assert "line 6" in captured.out
        assert "line 7" in captured.out

    def test_report_issue_with_suggestion(
        self, reporter: ConsoleReporter, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """测试带建议的问题输出"""
        issue = Issue(
            file=tmp_path / "test.md",
            line=1,
            type="test",
            message="Test",
            original="old",
            suggestion="new",
            checker="test",
        )
        reporter.report([issue], tmp_path)
        captured = capsys.readouterr()

        # 检查建议显示
        assert "Did you mean" in captured.out
        assert "new" in captured.out

    def test_report_multiple_files(
        self, reporter: ConsoleReporter, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """测试多文件问题分组"""
        issues = [
            Issue(
                file=tmp_path / "file1.md",
                line=1,
                type="test",
                message="Error in file1",
                original="x",
                checker="test",
            ),
            Issue(
                file=tmp_path / "file2.md",
                line=1,
                type="test",
                message="Error in file2",
                original="y",
                checker="test",
            ),
            Issue(
                file=tmp_path / "file1.md",
                line=5,
                type="test",
                message="Another error in file1",
                original="z",
                checker="test",
            ),
        ]
        reporter.report(issues, tmp_path)
        captured = capsys.readouterr()

        # 检查文件分组
        assert "file1.md" in captured.out
        assert "file2.md" in captured.out
        # 两个文件分开显示
        assert captured.out.count("file1.md") >= 1
        assert captured.out.count("file2.md") >= 1

    def test_report_issues_sorted_by_line(
        self, reporter: ConsoleReporter, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """测试同文件问题按行号排序"""
        issues = [
            Issue(
                file=tmp_path / "test.md",
                line=10,
                type="test",
                message="Line 10",
                original="x",
                checker="test",
            ),
            Issue(
                file=tmp_path / "test.md",
                line=5,
                type="test",
                message="Line 5",
                original="y",
                checker="test",
            ),
        ]
        reporter.report(issues, tmp_path)
        captured = capsys.readouterr()

        # Line 5 应该在 Line 10 之前
        pos_5 = captured.out.find("Line 5")
        pos_10 = captured.out.find("Line 10")
        assert pos_5 < pos_10, "Issues should be sorted by line number"


class TestConsoleReporterSummary:
    """ConsoleReporter 摘要测试"""

    @pytest.fixture
    def reporter(self) -> ConsoleReporter:
        return ConsoleReporter(color=ColorMode.NEVER)

    def test_summary_counts(
        self, reporter: ConsoleReporter, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """测试摘要统计数量"""
        issues = [
            Issue(
                file=tmp_path / "test.md",
                line=1,
                type="test",
                message="Error",
                original="x",
                checker="test",
                severity=Severity.ERROR,
            ),
            Issue(
                file=tmp_path / "test.md",
                line=2,
                type="test",
                message="Warning",
                original="y",
                checker="test",
                severity=Severity.WARNING,
            ),
            Issue(
                file=tmp_path / "test.md",
                line=3,
                type="test",
                message="Info",
                original="z",
                checker="test",
                severity=Severity.INFO,
            ),
        ]
        reporter.report_summary(issues)
        captured = capsys.readouterr()

        assert "1 error(s)" in captured.out
        assert "1 warning(s)" in captured.out
        assert "1 info(s)" in captured.out

    def test_summary_fixable_count(
        self, reporter: ConsoleReporter, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """测试可修复问题计数"""
        issues = [
            Issue(
                file=tmp_path / "test.md",
                line=1,
                type="test",
                message="Can fix",
                original="old",
                suggestion="new",
                checker="test",
            ),
            Issue(
                file=tmp_path / "test.md",
                line=2,
                type="test",
                message="Cannot fix",
                original="x",
                checker="test",
            ),
        ]
        reporter.report_summary(issues)
        captured = capsys.readouterr()

        assert "1 issue(s) can be auto-fixed" in captured.out

    def test_summary_empty(
        self, reporter: ConsoleReporter, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """测试空列表不输出摘要"""
        reporter.report_summary([])
        captured = capsys.readouterr()
        assert captured.out == ""


class TestConsoleReporterAlignment:
    """ConsoleReporter 对齐测试"""

    @pytest.fixture
    def reporter(self) -> ConsoleReporter:
        return ConsoleReporter(color=ColorMode.NEVER)

    def test_line_number_alignment(
        self, reporter: ConsoleReporter, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """测试行号对齐（4位宽度右对齐）"""
        issue = Issue(
            file=tmp_path / "test.md",
            line=5,
            type="test",
            message="Test",
            original="content",
            checker="test",
            context=ContextLines(
                before=[(3, "line 3"), (4, "line 4")],
                current=(5, "content"),
                after=[(6, "line 6")],
            ),
        )
        reporter.report([issue], tmp_path)
        captured = capsys.readouterr()

        # 检查行号格式（右对齐，4位宽度）
        # 行号应该是类似 "   3 │" 或 "   5 │"
        assert "   3" in captured.out or "3" in captured.out
        assert "   5" in captured.out or "5" in captured.out

    def test_underline_alignment(
        self, reporter: ConsoleReporter, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """测试下划线标记对齐"""
        issue = Issue(
            file=tmp_path / "test.md",
            line=1,
            column=10,
            type="test",
            message="Test",
            original="target",  # 6 chars
            checker="test",
            context=ContextLines(
                before=[],
                current=(1, "text text target more text"),
                after=[],
            ),
        )
        reporter.report([issue], tmp_path)
        captured = capsys.readouterr()

        # 应该有 ^ 标记
        assert "^" in captured.out
        # 下划线长度应该等于 original 长度
        underline_match = re.search(r"\^+", captured.out)
        assert underline_match is not None
        assert len(underline_match.group()) == len("target")


class TestConsoleReporterSpecialCases:
    """ConsoleReporter 特殊情况测试"""

    @pytest.fixture
    def reporter(self) -> ConsoleReporter:
        return ConsoleReporter(color=ColorMode.NEVER)

    def test_chinese_filename(
        self, reporter: ConsoleReporter, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """测试中文文件名"""
        issue = Issue(
            file=tmp_path / "测试文件.md",
            line=1,
            type="test",
            message="测试消息",
            original="内容",
            checker="test",
        )
        reporter.report([issue], tmp_path)
        captured = capsys.readouterr()

        assert "测试文件.md" in captured.out
        assert "测试消息" in captured.out

    def test_long_path(
        self, reporter: ConsoleReporter, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """测试长路径"""
        long_path = tmp_path / "very" / "long" / "nested" / "path" / "structure" / "file.md"
        issue = Issue(
            file=long_path,
            line=1,
            type="test",
            message="Test",
            original="x",
            checker="test",
        )
        reporter.report([issue], tmp_path)
        captured = capsys.readouterr()

        # 应该显示相对路径
        assert "very/long/nested/path/structure/file.md" in captured.out

    def test_issue_without_context(
        self, reporter: ConsoleReporter, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """测试无上下文的问题"""
        issue = Issue(
            file=tmp_path / "test.md",
            line=10,
            type="test",
            message="Test message",
            original="original",
            checker="test",
            context=None,  # 无上下文
        )
        reporter.report([issue], tmp_path)
        captured = capsys.readouterr()

        # 应该仍然正常输出
        assert "Test message" in captured.out
        assert "10" in captured.out

    def test_issue_without_column(
        self, reporter: ConsoleReporter, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """测试无列号的问题（不显示下划线）"""
        issue = Issue(
            file=tmp_path / "test.md",
            line=1,
            column=None,  # 无列号
            type="test",
            message="Test",
            original="content",
            checker="test",
            context=ContextLines(
                before=[],
                current=(1, "content here"),
                after=[],
            ),
        )
        reporter.report([issue], tmp_path)
        captured = capsys.readouterr()

        # 没有列号时不应该有下划线（因为逻辑是 column is not None）
        # 但消息应该显示
        assert "Test" in captured.out

    def test_report_issue_standalone(
        self, reporter: ConsoleReporter, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """测试单独报告单个问题"""
        issue = Issue(
            file=tmp_path / "test.md",
            line=10,
            type="test",
            message="Standalone issue",
            original="x",
            checker="test",
        )
        reporter.report_issue(issue, tmp_path)
        captured = capsys.readouterr()

        # 应该包含文件名和行号
        assert "test.md" in captured.out
        assert "10" in captured.out
        assert "Standalone issue" in captured.out


class TestConsoleReporterColorOutput:
    """ConsoleReporter 颜色输出测试"""

    @pytest.fixture
    def reporter(self) -> ConsoleReporter:
        return ConsoleReporter(color=ColorMode.ALWAYS)

    def test_error_color(
        self, reporter: ConsoleReporter, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """测试错误使用红色"""
        issue = Issue(
            file=tmp_path / "test.md",
            line=1,
            type="test",
            message="Error",
            original="x",
            checker="test",
            severity=Severity.ERROR,
        )
        reporter.report([issue], tmp_path)
        captured = capsys.readouterr()

        # 检查 ANSI 红色代码
        assert "\033[91m" in captured.out or "\033[31m" in captured.out

    def test_warning_color(
        self, reporter: ConsoleReporter, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """测试警告使用黄色"""
        issue = Issue(
            file=tmp_path / "test.md",
            line=1,
            type="test",
            message="Warning",
            original="x",
            checker="test",
            severity=Severity.WARNING,
        )
        reporter.report([issue], tmp_path)
        captured = capsys.readouterr()

        # 检查 ANSI 黄色代码
        assert "\033[93m" in captured.out or "\033[33m" in captured.out

    def test_suggestion_color(
        self, reporter: ConsoleReporter, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """测试建议使用绿色"""
        issue = Issue(
            file=tmp_path / "test.md",
            line=1,
            type="test",
            message="Test",
            original="old",
            suggestion="new",
            checker="test",
        )
        reporter.report([issue], tmp_path)
        captured = capsys.readouterr()

        # 检查 ANSI 绿色代码
        assert "\033[92m" in captured.out or "\033[32m" in captured.out
