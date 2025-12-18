"""Tests for InteractiveFixer - 交互式修复器测试

测试场景包括：
1. 用户输入处理（y/n/a/q/d/?）
2. 修复流程控制
3. 输出显示
4. 边界情况处理
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from checks.core.issue import Issue, Severity
from checks.fixers.base import FixAction, FixResult, FixSession
from checks.fixers.interactive import InteractiveFixer
from checks.reporters.console import ColorMode, ConsoleReporter


class TestInteractiveFixerBasic:
    """InteractiveFixer 基础功能测试"""

    @pytest.fixture
    def fixer(self) -> InteractiveFixer:
        """创建修复器实例"""
        return InteractiveFixer(
            reporter=ConsoleReporter(color=ColorMode.NEVER),
        )

    @pytest.fixture
    def sample_issue(self, tmp_path: Path) -> Issue:
        """创建示例可修复问题"""
        return Issue(
            file=tmp_path / "test.md",
            line=5,
            column=10,
            type="broken_image",
            message="Image not found",
            original="![alt](missing.png)",
            suggestion="![alt](existing.png)",
            checker="image",
            severity=Severity.ERROR,
        )

    @pytest.fixture
    def non_fixable_issue(self, tmp_path: Path) -> Issue:
        """创建不可修复问题（无建议）"""
        return Issue(
            file=tmp_path / "test.md",
            line=10,
            type="test",
            message="Cannot fix this",
            original="content",
            suggestion=None,  # 无建议
            checker="test",
        )

    def test_filter_fixable(
        self, fixer: InteractiveFixer, sample_issue: Issue, non_fixable_issue: Issue
    ) -> None:
        """测试过滤可修复问题"""
        issues = [sample_issue, non_fixable_issue]
        fixable = fixer.filter_fixable(issues)

        assert len(fixable) == 1
        assert sample_issue in fixable
        assert non_fixable_issue not in fixable

    def test_can_fix(
        self, fixer: InteractiveFixer, sample_issue: Issue, non_fixable_issue: Issue
    ) -> None:
        """测试判断是否可修复"""
        assert fixer.can_fix(sample_issue) is True
        assert fixer.can_fix(non_fixable_issue) is False


class TestInteractiveFixerPrompt:
    """InteractiveFixer 提示功能测试"""

    @pytest.fixture
    def fixer(self) -> InteractiveFixer:
        return InteractiveFixer(
            reporter=ConsoleReporter(color=ColorMode.NEVER),
        )

    @pytest.fixture
    def sample_issue(self, tmp_path: Path) -> Issue:
        return Issue(
            file=tmp_path / "test.md",
            line=5,
            type="test",
            message="Test",
            original="old",
            suggestion="new",
            checker="test",
        )

    def test_prompt_yes(self, fixer: InteractiveFixer, sample_issue: Issue, tmp_path: Path) -> None:
        """测试输入 y 返回 ACCEPT"""
        with patch("builtins.input", return_value="y"):
            action = fixer._prompt_action(sample_issue, tmp_path)
            assert action == FixAction.ACCEPT

    def test_prompt_yes_full(
        self, fixer: InteractiveFixer, sample_issue: Issue, tmp_path: Path
    ) -> None:
        """测试输入 yes 返回 ACCEPT"""
        with patch("builtins.input", return_value="yes"):
            action = fixer._prompt_action(sample_issue, tmp_path)
            assert action == FixAction.ACCEPT

    def test_prompt_no(self, fixer: InteractiveFixer, sample_issue: Issue, tmp_path: Path) -> None:
        """测试输入 n 返回 SKIP"""
        with patch("builtins.input", return_value="n"):
            action = fixer._prompt_action(sample_issue, tmp_path)
            assert action == FixAction.SKIP

    def test_prompt_no_full(
        self, fixer: InteractiveFixer, sample_issue: Issue, tmp_path: Path
    ) -> None:
        """测试输入 no 返回 SKIP"""
        with patch("builtins.input", return_value="no"):
            action = fixer._prompt_action(sample_issue, tmp_path)
            assert action == FixAction.SKIP

    def test_prompt_all(self, fixer: InteractiveFixer, sample_issue: Issue, tmp_path: Path) -> None:
        """测试输入 a 返回 ACCEPT_ALL"""
        with patch("builtins.input", return_value="a"):
            action = fixer._prompt_action(sample_issue, tmp_path)
            assert action == FixAction.ACCEPT_ALL

    def test_prompt_all_full(
        self, fixer: InteractiveFixer, sample_issue: Issue, tmp_path: Path
    ) -> None:
        """测试输入 all 返回 ACCEPT_ALL"""
        with patch("builtins.input", return_value="all"):
            action = fixer._prompt_action(sample_issue, tmp_path)
            assert action == FixAction.ACCEPT_ALL

    def test_prompt_quit(
        self, fixer: InteractiveFixer, sample_issue: Issue, tmp_path: Path
    ) -> None:
        """测试输入 q 返回 QUIT"""
        with patch("builtins.input", return_value="q"):
            action = fixer._prompt_action(sample_issue, tmp_path)
            assert action == FixAction.QUIT

    def test_prompt_quit_full(
        self, fixer: InteractiveFixer, sample_issue: Issue, tmp_path: Path
    ) -> None:
        """测试输入 quit 返回 QUIT"""
        with patch("builtins.input", return_value="quit"):
            action = fixer._prompt_action(sample_issue, tmp_path)
            assert action == FixAction.QUIT

    def test_prompt_empty_default_skip(
        self, fixer: InteractiveFixer, sample_issue: Issue, tmp_path: Path
    ) -> None:
        """测试空输入默认返回 SKIP"""
        with patch("builtins.input", return_value=""):
            action = fixer._prompt_action(sample_issue, tmp_path)
            assert action == FixAction.SKIP

    def test_prompt_eof_quit(
        self, fixer: InteractiveFixer, sample_issue: Issue, tmp_path: Path
    ) -> None:
        """测试 EOF 返回 QUIT"""
        with patch("builtins.input", side_effect=EOFError):
            action = fixer._prompt_action(sample_issue, tmp_path)
            assert action == FixAction.QUIT

    def test_prompt_keyboard_interrupt(
        self, fixer: InteractiveFixer, sample_issue: Issue, tmp_path: Path
    ) -> None:
        """测试 Ctrl+C 返回 QUIT"""
        with patch("builtins.input", side_effect=KeyboardInterrupt):
            action = fixer._prompt_action(sample_issue, tmp_path)
            assert action == FixAction.QUIT

    def test_prompt_diff_then_accept(
        self,
        fixer: InteractiveFixer,
        sample_issue: Issue,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """测试先查看 diff 然后接受"""
        with patch("builtins.input", side_effect=["d", "y"]):
            action = fixer._prompt_action(sample_issue, tmp_path)
            assert action == FixAction.ACCEPT

            # 检查 diff 输出
            captured = capsys.readouterr()
            assert "Original" in captured.out
            assert "Fixed" in captured.out

    def test_prompt_help_then_skip(
        self,
        fixer: InteractiveFixer,
        sample_issue: Issue,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """测试先查看帮助然后跳过"""
        with patch("builtins.input", side_effect=["?", "n"]):
            action = fixer._prompt_action(sample_issue, tmp_path)
            assert action == FixAction.SKIP

            # 检查帮助输出
            captured = capsys.readouterr()
            assert "Accept this fix" in captured.out

    def test_prompt_invalid_then_valid(
        self,
        fixer: InteractiveFixer,
        sample_issue: Issue,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """测试无效输入后有效输入"""
        with patch("builtins.input", side_effect=["invalid", "y"]):
            action = fixer._prompt_action(sample_issue, tmp_path)
            assert action == FixAction.ACCEPT

            # 检查错误提示
            captured = capsys.readouterr()
            assert "Unknown option" in captured.out

    def test_prompt_case_insensitive(
        self, fixer: InteractiveFixer, sample_issue: Issue, tmp_path: Path
    ) -> None:
        """测试大小写不敏感"""
        with patch("builtins.input", return_value="Y"):
            action = fixer._prompt_action(sample_issue, tmp_path)
            assert action == FixAction.ACCEPT

        with patch("builtins.input", return_value="YES"):
            action = fixer._prompt_action(sample_issue, tmp_path)
            assert action == FixAction.ACCEPT


class TestInteractiveFixerDiffPreview:
    """InteractiveFixer diff 预览测试"""

    @pytest.fixture
    def fixer(self) -> InteractiveFixer:
        return InteractiveFixer(
            reporter=ConsoleReporter(color=ColorMode.NEVER),
        )

    def test_show_diff_preview(
        self,
        fixer: InteractiveFixer,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """测试 diff 预览显示"""
        issue = Issue(
            file=tmp_path / "test.md",
            line=1,
            type="test",
            message="Test",
            original="old content",
            suggestion="new content",
            checker="test",
        )
        fixer._show_diff_preview(issue, tmp_path)
        captured = capsys.readouterr()

        assert "--- Original" in captured.out
        assert "- old content" in captured.out
        assert "+++ Fixed" in captured.out
        assert "+ new content" in captured.out

    def test_show_diff_preview_no_fix(
        self,
        fixer: InteractiveFixer,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """测试无修复方案时的 diff 预览"""
        issue = Issue(
            file=tmp_path / "test.md",
            line=1,
            type="test",
            message="Test",
            original="content",
            suggestion=None,  # 无建议
            checker="test",
        )
        fixer._show_diff_preview(issue, tmp_path)
        captured = capsys.readouterr()

        assert "No fix available" in captured.out


class TestInteractiveFixerFlow:
    """InteractiveFixer 流程测试"""

    @pytest.fixture
    def fixer(self) -> InteractiveFixer:
        return InteractiveFixer(
            reporter=ConsoleReporter(color=ColorMode.NEVER),
        )

    def test_fix_no_fixable_issues(
        self,
        fixer: InteractiveFixer,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """测试无可修复问题时的输出"""
        issues = [
            Issue(
                file=tmp_path / "test.md",
                line=1,
                type="test",
                message="Not fixable",
                original="x",
                suggestion=None,
                checker="test",
            )
        ]

        session = fixer.fix(issues, tmp_path, dry_run=True)
        captured = capsys.readouterr()

        assert "No fixable issues found" in captured.out
        assert len(session.results) == 0

    def test_fix_skip_all(
        self,
        fixer: InteractiveFixer,
        tmp_path: Path,
    ) -> None:
        """测试跳过所有问题"""
        issues = [
            Issue(
                file=tmp_path / "test.md",
                line=1,
                type="test",
                message="Issue 1",
                original="old1",
                suggestion="new1",
                checker="test",
            ),
            Issue(
                file=tmp_path / "test.md",
                line=2,
                type="test",
                message="Issue 2",
                original="old2",
                suggestion="new2",
                checker="test",
            ),
        ]

        with patch("builtins.input", return_value="n"):
            session = fixer.fix(issues, tmp_path, dry_run=True)

        assert len(session.results) == 2
        assert all(r.action == FixAction.SKIP for r in session.results)

    def test_fix_accept_first_skip_second(
        self,
        fixer: InteractiveFixer,
        tmp_path: Path,
    ) -> None:
        """测试接受第一个，跳过第二个"""
        issues = [
            Issue(
                file=tmp_path / "test.md",
                line=1,
                type="test",
                message="Issue 1",
                original="old1",
                suggestion="new1",
                checker="test",
            ),
            Issue(
                file=tmp_path / "test.md",
                line=2,
                type="test",
                message="Issue 2",
                original="old2",
                suggestion="new2",
                checker="test",
            ),
        ]

        with patch("builtins.input", side_effect=["y", "n"]):
            session = fixer.fix(issues, tmp_path, dry_run=True)

        assert len(session.results) == 2
        assert session.results[0].action == FixAction.ACCEPT
        assert session.results[1].action == FixAction.SKIP

    def test_fix_quit_early(
        self,
        fixer: InteractiveFixer,
        tmp_path: Path,
    ) -> None:
        """测试提前退出

        quit 会立即中断循环，所以第二个问题不会被记录到 results 中。
        只有被处理过的问题（接受/跳过）才会有结果。
        """
        issues = [
            Issue(
                file=tmp_path / "test.md",
                line=i,
                type="test",
                message=f"Issue {i}",
                original=f"old{i}",
                suggestion=f"new{i}",
                checker="test",
            )
            for i in range(1, 6)
        ]

        # 接受第一个，然后退出
        with patch("builtins.input", side_effect=["y", "q"]):
            session = fixer.fix(issues, tmp_path, dry_run=True)

        # quit 中断循环，第二个问题没有被记录
        # 只有第一个被接受的问题有结果
        assert len(session.results) == 1
        assert session.results[0].action == FixAction.ACCEPT

    def test_fix_accept_all(
        self,
        fixer: InteractiveFixer,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """测试接受所有"""
        issues = [
            Issue(
                file=tmp_path / "test.md",
                line=i,
                type="test",
                message=f"Issue {i}",
                original=f"old{i}",
                suggestion=f"new{i}",
                checker="test",
            )
            for i in range(1, 4)
        ]

        # 接受第一个后选择 all
        with patch("builtins.input", side_effect=["a"]):
            session = fixer.fix(issues, tmp_path, dry_run=True)

        # 所有问题都应该被接受
        assert len(session.results) == 3
        assert all(r.action == FixAction.ACCEPT for r in session.results)

        captured = capsys.readouterr()
        assert "Accepting all remaining" in captured.out


class TestInteractiveFixerSummary:
    """InteractiveFixer 摘要测试"""

    @pytest.fixture
    def fixer(self) -> InteractiveFixer:
        return InteractiveFixer(
            reporter=ConsoleReporter(color=ColorMode.NEVER),
        )

    def test_print_summary(
        self,
        fixer: InteractiveFixer,
        capsys: pytest.CaptureFixture[str],
        tmp_path: Path,
    ) -> None:
        """测试摘要打印"""
        session = FixSession()
        issue = Issue(
            file=tmp_path / "test.md",
            line=1,
            type="test",
            message="Test",
            original="old",
            suggestion="new",
            checker="test",
        )
        session.results = [
            FixResult(issue=issue, action=FixAction.ACCEPT, applied=True),
            FixResult(issue=issue, action=FixAction.ACCEPT, applied=False),
            FixResult(issue=issue, action=FixAction.SKIP),
        ]

        fixer._print_summary(session)
        captured = capsys.readouterr()

        assert "Summary" in captured.out
        assert "1 fix(es) applied" in captured.out
        assert "1 fix(es) pending" in captured.out
        assert "1 issue(s) skipped" in captured.out


class TestInteractiveFixerIntegration:
    """InteractiveFixer 集成测试"""

    @pytest.fixture
    def test_file(self, tmp_path: Path) -> Path:
        """创建测试文件"""
        file = tmp_path / "test.md"
        file.write_text("line1\nold content\nline3\n", encoding="utf-8")
        return file

    def test_fix_applies_changes(self, tmp_path: Path, test_file: Path) -> None:
        """测试修复确实应用了更改"""
        fixer = InteractiveFixer(
            reporter=ConsoleReporter(color=ColorMode.NEVER),
        )

        issues = [
            Issue(
                file=test_file,
                line=2,
                type="test",
                message="Fix this",
                original="old content",
                suggestion="new content",
                checker="test",
            )
        ]

        # Mock PatchFixer 的 fix 方法来避免实际文件操作
        with patch.object(fixer.patch_fixer, "fix") as mock_fix:
            mock_session = FixSession()
            mock_fix.return_value = mock_session

            with patch("builtins.input", return_value="y"):
                fixer.fix(issues, tmp_path, dry_run=False)

        # 验证调用
        assert mock_fix.called

    def test_dry_run_no_changes(self, tmp_path: Path, test_file: Path) -> None:
        """测试 dry-run 不修改文件"""
        original_content = test_file.read_text(encoding="utf-8")

        fixer = InteractiveFixer(
            reporter=ConsoleReporter(color=ColorMode.NEVER),
        )

        issues = [
            Issue(
                file=test_file,
                line=2,
                type="test",
                message="Fix this",
                original="old content",
                suggestion="new content",
                checker="test",
            )
        ]

        with patch("builtins.input", return_value="y"):
            fixer.fix(issues, tmp_path, dry_run=True)

        # 文件内容应该没有变化
        assert test_file.read_text(encoding="utf-8") == original_content
