"""Tests for core.issue module"""

from pathlib import Path

from checks.core.issue import ContextLines, Fix, Issue, Severity


class TestSeverity:
    """Severity 枚举测试"""

    def test_severity_values(self) -> None:
        """测试严重程度值"""
        assert Severity.ERROR.value == "error"
        assert Severity.WARNING.value == "warning"
        assert Severity.INFO.value == "info"

    def test_severity_str(self) -> None:
        """测试字符串转换"""
        assert str(Severity.ERROR) == "error"
        assert str(Severity.WARNING) == "warning"


class TestContextLines:
    """ContextLines 测试"""

    def test_all_lines(self) -> None:
        """测试获取所有行"""
        ctx = ContextLines(
            before=[(1, "line 1"), (2, "line 2")],
            current=(3, "current line"),
            after=[(4, "line 4"), (5, "line 5")],
        )

        all_lines = ctx.all_lines
        assert len(all_lines) == 5
        assert all_lines[0] == (1, "line 1")
        assert all_lines[2] == (3, "current line")
        assert all_lines[4] == (5, "line 5")

    def test_empty_context(self) -> None:
        """测试空上下文"""
        ctx = ContextLines(
            before=[],
            current=(1, "only line"),
            after=[],
        )

        assert len(ctx.all_lines) == 1
        assert ctx.current == (1, "only line")


class TestFix:
    """Fix 测试"""

    def test_apply_to_line_simple(self) -> None:
        """测试简单替换"""
        fix = Fix(
            original="old_text",
            replacement="new_text",
            line=1,
        )

        result = fix.apply_to_line("This is old_text here")
        assert result == "This is new_text here"

    def test_apply_to_line_with_column(self) -> None:
        """测试精确位置替换"""
        fix = Fix(
            original="old",
            replacement="new",
            line=1,
            start_col=5,
            end_col=8,
        )

        result = fix.apply_to_line("This old world")
        assert result == "This new world"

    def test_apply_to_line_with_start_col_no_end_col(self) -> None:
        """测试有 start_col 但无 end_col 时自动计算 end_col

        回归测试：修复 bug，之前 end_col 为 None 时导致错误替换，
        出现 '![alt](new.png)![alt](old.png)' 这样的重复内容。
        """
        fix = Fix(
            original="![alt](old.png)",
            replacement="![alt](new.png)",
            line=1,
            start_col=0,
            end_col=None,  # 未设置 end_col
        )

        result = fix.apply_to_line("![alt](old.png)")
        assert result == "![alt](new.png)"
        # 确保没有重复
        assert result.count("![alt]") == 1

    def test_apply_to_line_middle_with_start_col_only(self) -> None:
        """测试行中间替换，只有 start_col"""
        fix = Fix(
            original="![img](old.png)",
            replacement="![img](new.png)",
            line=1,
            start_col=10,
            end_col=None,
        )

        result = fix.apply_to_line("Some text ![img](old.png) more text")
        assert result == "Some text ![img](new.png) more text"

    def test_apply_to_line_first_occurrence(self) -> None:
        """测试只替换第一次出现"""
        fix = Fix(
            original="test",
            replacement="TEST",
            line=1,
        )

        result = fix.apply_to_line("test and test again")
        assert result == "TEST and test again"


class TestIssue:
    """Issue 测试"""

    def test_issue_creation(self) -> None:
        """测试创建 Issue"""
        issue = Issue(
            file=Path("test.md"),
            line=10,
            type="broken_image",
            message="Image not found",
            original="![](missing.png)",
            checker="image",
        )

        assert issue.file == Path("test.md")
        assert issue.line == 10
        assert issue.severity == Severity.ERROR  # default
        assert issue.column is None
        assert issue.suggestion is None

    def test_issue_path_conversion(self) -> None:
        """测试路径自动转换"""
        issue = Issue(
            file="string/path.md",  # type: ignore
            line=1,
            type="test",
            message="test",
            original="test",
            checker="test",
        )

        assert isinstance(issue.file, Path)
        assert issue.file == Path("string/path.md")

    def test_has_suggestion(self) -> None:
        """测试是否有建议"""
        issue_without = Issue(
            file=Path("test.md"),
            line=1,
            type="test",
            message="test",
            original="test",
            checker="test",
        )
        assert not issue_without.has_suggestion

        issue_with = Issue(
            file=Path("test.md"),
            line=1,
            type="test",
            message="test",
            original="test",
            suggestion="fixed",
            checker="test",
        )
        assert issue_with.has_suggestion

    def test_location_without_column(self) -> None:
        """测试位置字符串（无列号）"""
        issue = Issue(
            file=Path("src/test.md"),
            line=42,
            type="test",
            message="test",
            original="test",
            checker="test",
        )

        # 使用 Path 匹配平台分隔符
        expected = f"{Path('src/test.md')}:42"
        assert issue.location == expected

    def test_location_with_column(self) -> None:
        """测试位置字符串（有列号）"""
        issue = Issue(
            file=Path("src/test.md"),
            line=42,
            column=10,
            type="test",
            message="test",
            original="test",
            checker="test",
        )

        # 使用 Path 匹配平台分隔符
        expected = f"{Path('src/test.md')}:42:10"
        assert issue.location == expected

    def test_get_fix(self) -> None:
        """测试获取修复方案"""
        issue = Issue(
            file=Path("test.md"),
            line=5,
            column=10,
            type="test",
            message="test",
            original="old",
            suggestion="new",
            checker="test",
        )

        fix = issue.get_fix()
        assert fix is not None
        assert fix.original == "old"
        assert fix.replacement == "new"
        assert fix.line == 5
        assert fix.start_col == 10

    def test_get_fix_no_suggestion(self) -> None:
        """测试无建议时获取修复"""
        issue = Issue(
            file=Path("test.md"),
            line=5,
            type="test",
            message="test",
            original="old",
            checker="test",
        )

        assert issue.get_fix() is None

    def test_str_representation(self) -> None:
        """测试字符串表示"""
        issue = Issue(
            file=Path("test.md"),
            line=10,
            type="broken_image",
            message="Image not found",
            original="test",
            checker="image",
        )

        # Severity 的 __str__ 返回小写值
        assert "[error]" in str(issue)
        assert "test.md:10" in str(issue)
        assert "Image not found" in str(issue)

    def test_repr(self) -> None:
        """测试 repr"""
        issue = Issue(
            file=Path("test.md"),
            line=10,
            type="broken_image",
            message="Image not found",
            original="test",
            checker="image",
        )

        repr_str = repr(issue)
        assert "Issue(" in repr_str
        assert "file=" in repr_str
        assert "line=10" in repr_str
