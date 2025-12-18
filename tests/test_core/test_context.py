"""Tests for CheckContext"""

from pathlib import Path

import pytest

from checks import CheckContext, Config
from checks.core.issue import ContextLines


class TestCheckContext:
    """CheckContext 测试"""

    @pytest.fixture
    def context(self, tmp_path: Path) -> CheckContext:
        """创建检查上下文"""
        config = Config(root=tmp_path)
        assert config.resolver is not None
        return CheckContext(root=tmp_path, config=config, resolver=config.resolver)

    def test_root_resolution(self, tmp_path: Path) -> None:
        """测试根目录解析为绝对路径"""
        config = Config(root=".")
        assert config.resolver is not None

        ctx = CheckContext(root=tmp_path, config=config, resolver=config.resolver)
        assert ctx.root.is_absolute()
        assert ctx.root == tmp_path.resolve()

    def test_read_file(self, context: CheckContext, tmp_path: Path) -> None:
        """测试文件读取"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!", encoding="utf-8")

        content = context.read_file(test_file)
        assert content == "Hello, World!"

    def test_read_file_cached(self, context: CheckContext, tmp_path: Path) -> None:
        """测试文件读取缓存"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Original", encoding="utf-8")

        # 第一次读取
        content1 = context.read_file(test_file)
        assert content1 == "Original"

        # 修改文件
        test_file.write_text("Modified", encoding="utf-8")

        # 第二次读取应该返回缓存的内容
        content2 = context.read_file(test_file)
        assert content2 == "Original"

    def test_read_file_not_found(self, context: CheckContext, tmp_path: Path) -> None:
        """测试读取不存在的文件"""
        with pytest.raises(FileNotFoundError):
            context.read_file(tmp_path / "nonexistent.txt")

    def test_get_file_lines(self, context: CheckContext, tmp_path: Path) -> None:
        """测试获取文件行"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Line 1\nLine 2\nLine 3", encoding="utf-8")

        lines = context.get_file_lines(test_file)
        assert len(lines) == 3
        assert lines[0] == "Line 1"
        assert lines[2] == "Line 3"

    def test_get_context_lines(self, context: CheckContext, tmp_path: Path) -> None:
        """测试获取上下文行"""
        test_file = tmp_path / "test.md"
        test_file.write_text(
            "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\nLine 6\nLine 7",
            encoding="utf-8",
        )

        ctx_lines = context.get_context_lines(test_file, line=4, before=2, after=2)

        assert isinstance(ctx_lines, ContextLines)
        assert len(ctx_lines.before) == 2
        assert ctx_lines.current == (4, "Line 4")
        assert len(ctx_lines.after) == 2

        # 检查具体内容
        assert ctx_lines.before[0] == (2, "Line 2")
        assert ctx_lines.before[1] == (3, "Line 3")
        assert ctx_lines.after[0] == (5, "Line 5")
        assert ctx_lines.after[1] == (6, "Line 6")

    def test_get_context_lines_at_start(self, context: CheckContext, tmp_path: Path) -> None:
        """测试获取文件开头的上下文"""
        test_file = tmp_path / "test.md"
        test_file.write_text("Line 1\nLine 2\nLine 3", encoding="utf-8")

        ctx_lines = context.get_context_lines(test_file, line=1, before=3, after=1)

        assert len(ctx_lines.before) == 0  # 没有前面的行
        assert ctx_lines.current == (1, "Line 1")
        assert len(ctx_lines.after) == 1

    def test_get_context_lines_at_end(self, context: CheckContext, tmp_path: Path) -> None:
        """测试获取文件末尾的上下文"""
        test_file = tmp_path / "test.md"
        test_file.write_text("Line 1\nLine 2\nLine 3", encoding="utf-8")

        ctx_lines = context.get_context_lines(test_file, line=3, before=1, after=3)

        assert len(ctx_lines.before) == 1
        assert ctx_lines.current == (3, "Line 3")
        assert len(ctx_lines.after) == 0  # 没有后面的行

    def test_relative_path(self, context: CheckContext, tmp_path: Path) -> None:
        """测试相对路径计算"""
        file_path = tmp_path / "subdir" / "test.md"

        rel_path = context.relative_path(file_path)
        assert rel_path == Path("subdir/test.md")

    def test_relative_path_outside_root(
        self,
        context: CheckContext,
        tmp_path: Path,  # noqa: ARG002
    ) -> None:
        """测试根目录外的路径"""
        outside_path = Path("/some/other/path/test.md")

        # 应该返回原路径
        rel_path = context.relative_path(outside_path)
        assert rel_path == outside_path

    def test_clear_cache(self, context: CheckContext, tmp_path: Path) -> None:
        """测试清空缓存"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Original", encoding="utf-8")

        # 读取并缓存
        context.read_file(test_file)
        assert len(context.file_cache) == 1

        # 清空缓存
        context.clear_cache()
        assert len(context.file_cache) == 0

        # 修改文件
        test_file.write_text("Modified", encoding="utf-8")

        # 重新读取应该获得新内容
        content = context.read_file(test_file)
        assert content == "Modified"
