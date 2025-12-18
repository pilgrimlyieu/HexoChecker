"""Tests for PatchFixer - Patch 修复器测试

测试场景包括：
1. Patch 生成
2. 单文件/多文件修复
3. 行号处理（边界情况）
4. Patch 文件保存
5. Patch 应用
6. 撤销功能
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from checks.core.issue import Fix, Issue
from checks.fixers.base import FixAction
from checks.fixers.patch import PatchFixer


class TestPatchFixerBasic:
    """PatchFixer 基础功能测试"""

    @pytest.fixture
    def fixer(self) -> PatchFixer:
        return PatchFixer()

    def test_default_attributes(self, fixer: PatchFixer) -> None:
        """测试默认属性"""
        assert fixer.name == "patch"
        assert fixer.context_lines == 3
        assert fixer.patch_dir == Path(".checks/patches")


class TestPatchFixerFixFile:
    """PatchFixer 单文件修复测试"""

    @pytest.fixture
    def fixer(self) -> PatchFixer:
        return PatchFixer()

    @pytest.fixture
    def test_file(self, tmp_path: Path) -> Path:
        """创建测试文件"""
        file = tmp_path / "test.md"
        file.write_text(
            "line 1\nold content here\nline 3\nline 4\nline 5\n",
            encoding="utf-8",
        )
        return file

    def test_fix_single_issue(self, fixer: PatchFixer, test_file: Path, tmp_path: Path) -> None:
        """测试修复单个问题"""
        issue = Issue(
            file=test_file,
            line=2,
            type="test",
            message="Fix this",
            original="old content",
            suggestion="new content",
            checker="test",
        )

        patch_str, results = fixer._fix_file(test_file, [issue], tmp_path)

        assert patch_str is not None
        assert len(results) == 1
        assert results[0].action == FixAction.ACCEPT
        assert "old content" in patch_str
        assert "new content" in patch_str

    def test_fix_multiple_issues_same_file(self, fixer: PatchFixer, tmp_path: Path) -> None:
        """测试同文件多个问题"""
        file = tmp_path / "multi.md"
        file.write_text(
            "line 1\nfix me\nline 3\nalso fix\nline 5\n",
            encoding="utf-8",
        )

        issues = [
            Issue(
                file=file,
                line=2,
                type="test",
                message="First",
                original="fix me",
                suggestion="fixed 1",
                checker="test",
            ),
            Issue(
                file=file,
                line=4,
                type="test",
                message="Second",
                original="also fix",
                suggestion="fixed 2",
                checker="test",
            ),
        ]

        patch_str, results = fixer._fix_file(file, issues, tmp_path)

        assert patch_str is not None
        assert len(results) == 2
        # 两个修复都应该成功
        assert all(r.action == FixAction.ACCEPT for r in results)

    def test_fix_issue_no_suggestion(
        self, fixer: PatchFixer, test_file: Path, tmp_path: Path
    ) -> None:
        """测试无建议的问题"""
        issue = Issue(
            file=test_file,
            line=2,
            type="test",
            message="No fix",
            original="old content",
            suggestion=None,  # 无建议
            checker="test",
        )

        patch_str, results = fixer._fix_file(test_file, [issue], tmp_path)

        # 没有实际修复，patch 应该为 None
        assert patch_str is None
        assert len(results) == 1
        assert results[0].action == FixAction.SKIP
        assert "No fix available" in (results[0].error or "")

    def test_fix_file_not_found(self, fixer: PatchFixer, tmp_path: Path) -> None:
        """测试文件不存在"""
        missing_file = tmp_path / "missing.md"
        issue = Issue(
            file=missing_file,
            line=1,
            type="test",
            message="Test",
            original="x",
            suggestion="y",
            checker="test",
        )

        patch_str, results = fixer._fix_file(missing_file, [issue], tmp_path)

        assert patch_str is None
        assert len(results) == 1
        assert results[0].action == FixAction.SKIP
        assert "Failed to read file" in (results[0].error or "")

    def test_fix_line_out_of_range(
        self, fixer: PatchFixer, test_file: Path, tmp_path: Path
    ) -> None:
        """测试行号超出范围"""
        issue = Issue(
            file=test_file,
            line=999,  # 超出文件行数
            type="test",
            message="Test",
            original="x",
            suggestion="y",
            checker="test",
        )

        _patch_str, results = fixer._fix_file(test_file, [issue], tmp_path)

        assert len(results) == 1
        assert results[0].action == FixAction.SKIP
        assert "out of range" in (results[0].error or "")

    def test_fix_first_line(self, fixer: PatchFixer, tmp_path: Path) -> None:
        """测试修复第一行"""
        file = tmp_path / "first.md"
        file.write_text("fix this\nline 2\nline 3\n", encoding="utf-8")

        issue = Issue(
            file=file,
            line=1,
            type="test",
            message="Fix",
            original="fix this",
            suggestion="fixed",
            checker="test",
        )

        patch_str, _results = fixer._fix_file(file, [issue], tmp_path)

        assert patch_str is not None
        assert "-fix this" in patch_str
        assert "+fixed" in patch_str

    def test_fix_last_line(self, fixer: PatchFixer, tmp_path: Path) -> None:
        """测试修复最后一行"""
        file = tmp_path / "last.md"
        file.write_text("line 1\nline 2\nfix this", encoding="utf-8")

        issue = Issue(
            file=file,
            line=3,
            type="test",
            message="Fix",
            original="fix this",
            suggestion="fixed",
            checker="test",
        )

        patch_str, results = fixer._fix_file(file, [issue], tmp_path)

        assert patch_str is not None
        assert results[0].action == FixAction.ACCEPT

    def test_fix_no_change_needed(self, fixer: PatchFixer, test_file: Path, tmp_path: Path) -> None:
        """测试内容没有变化（original 不在文件中）"""
        issue = Issue(
            file=test_file,
            line=2,
            type="test",
            message="Fix",
            original="nonexistent text",
            suggestion="new text",
            checker="test",
        )

        _patch_str, results = fixer._fix_file(test_file, [issue], tmp_path)

        # 替换不会改变内容（因为 original 不存在），所以没有 patch
        # 但 FixResult 仍然标记为 ACCEPT
        assert results[0].action == FixAction.ACCEPT


class TestPatchFixerSession:
    """PatchFixer 会话测试"""

    @pytest.fixture
    def fixer(self) -> PatchFixer:
        return PatchFixer()

    def test_fix_empty_issues(self, fixer: PatchFixer, tmp_path: Path) -> None:
        """测试空问题列表"""
        session = fixer.fix([], tmp_path, dry_run=True)

        assert len(session.results) == 0
        assert session.completed_at is not None

    def test_fix_dry_run(self, fixer: PatchFixer, tmp_path: Path) -> None:
        """测试 dry-run 模式"""
        file = tmp_path / "test.md"
        original_content = "old content\n"
        file.write_text(original_content, encoding="utf-8")

        issues = [
            Issue(
                file=file,
                line=1,
                type="test",
                message="Fix",
                original="old content",
                suggestion="new content",
                checker="test",
            )
        ]

        fixer.fix(issues, tmp_path, dry_run=True)

        # dry-run 不应该修改文件
        assert file.read_text(encoding="utf-8") == original_content
        # 不应该创建 patch 文件
        patch_dir = tmp_path / fixer.patch_dir
        assert not patch_dir.exists() or len(list(patch_dir.glob("*.patch"))) == 0

    def test_fix_multiple_files(self, fixer: PatchFixer, tmp_path: Path) -> None:
        """测试多文件修复"""
        file1 = tmp_path / "file1.md"
        file1.write_text("content1\n", encoding="utf-8")

        file2 = tmp_path / "file2.md"
        file2.write_text("content2\n", encoding="utf-8")

        issues = [
            Issue(
                file=file1,
                line=1,
                type="test",
                message="Fix1",
                original="content1",
                suggestion="fixed1",
                checker="test",
            ),
            Issue(
                file=file2,
                line=1,
                type="test",
                message="Fix2",
                original="content2",
                suggestion="fixed2",
                checker="test",
            ),
        ]

        session = fixer.fix(issues, tmp_path, dry_run=True)

        assert len(session.results) == 2


class TestPatchFixerPatchFile:
    """PatchFixer Patch 文件测试"""

    @pytest.fixture
    def fixer(self) -> PatchFixer:
        return PatchFixer()

    def test_save_patch(self, fixer: PatchFixer, tmp_path: Path) -> None:
        """测试保存 patch 文件"""
        patch_content = "--- a/test.md\n+++ b/test.md\n@@ -1 +1 @@\n-old\n+new\n"
        session_id = "test_session"

        patch_file = fixer._save_patch(patch_content, session_id, tmp_path)

        assert patch_file.exists()
        assert patch_file.read_text(encoding="utf-8") == patch_content
        assert session_id in patch_file.name
        assert patch_file.suffix == ".patch"

    def test_list_patches(self, fixer: PatchFixer, tmp_path: Path) -> None:
        """测试列出 patch 文件"""
        patch_dir = tmp_path / fixer.patch_dir
        patch_dir.mkdir(parents=True)

        # 创建几个 patch 文件
        (patch_dir / "2024-01-01_120000_s1.patch").write_text("p1", encoding="utf-8")
        (patch_dir / "2024-01-02_120000_s2.patch").write_text("p2", encoding="utf-8")
        (patch_dir / "2024-01-03_120000_s3.patch").write_text("p3", encoding="utf-8")

        patches = fixer.list_patches(tmp_path)

        assert len(patches) == 3
        # 应该按时间倒序排列
        assert "2024-01-03" in patches[0].name

    def test_list_patches_empty(self, fixer: PatchFixer, tmp_path: Path) -> None:
        """测试空 patch 目录"""
        patches = fixer.list_patches(tmp_path)
        assert patches == []

    def test_get_latest_patch(self, fixer: PatchFixer, tmp_path: Path) -> None:
        """测试获取最新 patch"""
        patch_dir = tmp_path / fixer.patch_dir
        patch_dir.mkdir(parents=True)

        (patch_dir / "2024-01-01_s1.patch").write_text("old", encoding="utf-8")
        (patch_dir / "2024-01-02_s2.patch").write_text("new", encoding="utf-8")

        latest = fixer.get_latest_patch(tmp_path)

        assert latest is not None
        assert "2024-01-02" in latest.name

    def test_get_latest_patch_none(self, fixer: PatchFixer, tmp_path: Path) -> None:
        """测试无 patch 时返回 None"""
        latest = fixer.get_latest_patch(tmp_path)
        assert latest is None

    def test_preview_patch(self, fixer: PatchFixer, tmp_path: Path) -> None:
        """测试预览 patch"""
        patch_dir = tmp_path / fixer.patch_dir
        patch_dir.mkdir(parents=True)

        content = "--- a/test.md\n+++ b/test.md\n"
        patch_file = patch_dir / "test.patch"
        patch_file.write_text(content, encoding="utf-8")

        preview = fixer.preview_patch(patch_file)
        assert preview == content


class TestPatchFixerApply:
    """PatchFixer 应用测试"""

    @pytest.fixture
    def fixer(self) -> PatchFixer:
        return PatchFixer()

    def test_apply_patch_git(self, fixer: PatchFixer, tmp_path: Path) -> None:
        """测试使用 git apply"""
        patch_file = tmp_path / "test.patch"
        patch_file.write_text("patch content", encoding="utf-8")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = fixer._apply_patch(patch_file, tmp_path)

        assert result is True
        mock_run.assert_called_once()
        # 应该使用 git apply
        assert "git" in mock_run.call_args[0][0]

    def test_apply_patch_fallback_patch_cmd(self, fixer: PatchFixer, tmp_path: Path) -> None:
        """测试回退到 patch 命令"""
        patch_file = tmp_path / "test.patch"
        patch_file.write_text("patch content", encoding="utf-8")

        with patch("subprocess.run") as mock_run:
            # git apply 失败，patch 成功
            mock_run.side_effect = [
                MagicMock(returncode=1),  # git apply 失败
                MagicMock(returncode=0),  # patch 成功
            ]
            result = fixer._apply_patch(patch_file, tmp_path)

        assert result is True
        assert mock_run.call_count == 2

    def test_apply_patch_manual_fallback(self, fixer: PatchFixer, tmp_path: Path) -> None:
        """测试手动应用 patch"""
        patch_file = tmp_path / "test.patch"
        patch_file.write_text("patch content", encoding="utf-8")

        with (
            patch("subprocess.run", side_effect=FileNotFoundError),
            patch.object(fixer, "_manual_apply_patch", return_value=True) as mock,
        ):
            result = fixer._apply_patch(patch_file, tmp_path)

        assert result is True
        mock.assert_called_once()


class TestPatchFixerUndo:
    """PatchFixer 撤销测试"""

    @pytest.fixture
    def fixer(self) -> PatchFixer:
        return PatchFixer()

    def test_undo_patch_git(self, fixer: PatchFixer, tmp_path: Path) -> None:
        """测试使用 git apply -R 撤销"""
        patch_file = tmp_path / "test.patch"
        patch_file.write_text("patch content", encoding="utf-8")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = fixer.undo(patch_file, tmp_path)

        assert result is True
        # 应该使用 -R 选项
        assert "-R" in mock_run.call_args[0][0]

    def test_undo_patch_fallback(self, fixer: PatchFixer, tmp_path: Path) -> None:
        """测试回退到 patch -R"""
        patch_file = tmp_path / "test.patch"
        patch_file.write_text("patch content", encoding="utf-8")

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=1),  # git 失败
                MagicMock(returncode=0),  # patch -R 成功
            ]
            result = fixer.undo(patch_file, tmp_path)

        assert result is True

    def test_undo_patch_no_tool(self, fixer: PatchFixer, tmp_path: Path) -> None:
        """测试无工具可用时返回 False"""
        patch_file = tmp_path / "test.patch"
        patch_file.write_text("patch content", encoding="utf-8")

        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = fixer.undo(patch_file, tmp_path)

        assert result is False


class TestPatchFixerManualApply:
    """PatchFixer 手动应用测试"""

    @pytest.fixture
    def fixer(self) -> PatchFixer:
        return PatchFixer()

    def test_manual_apply_simple(self, fixer: PatchFixer, tmp_path: Path) -> None:
        """测试简单手动应用"""
        # 创建测试文件
        test_file = tmp_path / "test.md"
        test_file.write_text("line 1\nold line\nline 3\n", encoding="utf-8")

        # 创建 patch
        patch_content = """--- a/test.md
+++ b/test.md
@@ -1,3 +1,3 @@
 line 1
-old line
+new line
 line 3
"""
        patch_file = tmp_path / "test.patch"
        patch_file.write_text(patch_content, encoding="utf-8")

        result = fixer._manual_apply_patch(patch_file, tmp_path)

        assert result is True
        content = test_file.read_text(encoding="utf-8")
        assert "new line" in content
        assert "old line" not in content

    def test_manual_apply_file_not_exists(self, fixer: PatchFixer, tmp_path: Path) -> None:
        """测试文件不存在时的手动应用"""
        patch_content = """--- a/missing.md
+++ b/missing.md
@@ -1 +1 @@
-old
+new
"""
        patch_file = tmp_path / "test.patch"
        patch_file.write_text(patch_content, encoding="utf-8")

        result = fixer._manual_apply_patch(patch_file, tmp_path)

        # 应该返回 True（跳过不存在的文件）
        assert result is True


class TestFixApplyToLine:
    """Fix.apply_to_line 测试"""

    def test_simple_replacement(self) -> None:
        """测试简单替换"""
        fix = Fix(
            original="old",
            replacement="new",
            line=1,
        )
        result = fix.apply_to_line("This has old text")
        assert result == "This has new text"

    def test_replacement_with_column(self) -> None:
        """测试精确列位置替换"""
        fix = Fix(
            original="old",
            replacement="new",
            line=1,
            start_col=9,
            end_col=12,
        )
        result = fix.apply_to_line("This has old text")
        assert result == "This has new text"

    def test_replacement_only_first(self) -> None:
        """测试只替换第一个匹配"""
        fix = Fix(
            original="test",
            replacement="TEST",
            line=1,
        )
        result = fix.apply_to_line("test and test again")
        assert result == "TEST and test again"

    def test_replacement_special_chars(self) -> None:
        """测试特殊字符"""
        fix = Fix(
            original="![alt](old.png)",
            replacement="![alt](new.png)",
            line=1,
        )
        result = fix.apply_to_line("See ![alt](old.png) here")
        assert result == "See ![alt](new.png) here"

    def test_replacement_chinese(self) -> None:
        """测试中文字符"""
        fix = Fix(
            original="旧内容",
            replacement="新内容",
            line=1,
        )
        result = fix.apply_to_line("这是旧内容测试")
        assert result == "这是新内容测试"


class TestPatchFixerIntegration:
    """PatchFixer 集成测试"""

    def test_full_workflow(self, tmp_path: Path) -> None:
        """测试完整工作流程"""
        # 创建测试文件
        file = tmp_path / "test.md"
        file.write_text("# Title\n\n![image](old.png)\n\nMore text\n", encoding="utf-8")

        # 创建问题
        issues = [
            Issue(
                file=file,
                line=3,
                type="broken_image",
                message="Image not found",
                original="old.png",
                suggestion="new.png",
                checker="image",
            )
        ]

        # 执行修复（模拟 git apply）
        fixer = PatchFixer()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            session = fixer.fix(issues, tmp_path, dry_run=False)

        # 验证结果
        assert len(session.results) == 1
        assert session.results[0].action == FixAction.ACCEPT

        # 验证 patch 文件已创建
        patches = fixer.list_patches(tmp_path)
        assert len(patches) == 1

        # 验证 patch 内容
        patch_content = patches[0].read_text(encoding="utf-8")
        assert "old.png" in patch_content
        assert "new.png" in patch_content
