"""Tests for HexoResolver"""

from pathlib import Path

import pytest

from checks import CheckContext, Config
from checks.resolvers import HexoResolver


class TestHexoResolver:
    """HexoResolver 测试"""

    @pytest.fixture
    def resolver(self) -> HexoResolver:
        """创建解析器实例"""
        return HexoResolver(post_dir="_posts", asset_folder_per_post=True)

    @pytest.fixture
    def context(self, tmp_path: Path, resolver: HexoResolver) -> CheckContext:
        """创建检查上下文"""
        config = Config(root=tmp_path, resolver=resolver)
        (tmp_path / "_posts").mkdir()
        (tmp_path / "pages").mkdir()
        return CheckContext(root=tmp_path, config=config, resolver=resolver)

    def test_is_external_http(self, resolver: HexoResolver) -> None:
        """测试 HTTP 外部链接检测"""
        assert resolver.is_external("http://example.com/image.png")
        assert resolver.is_external("https://example.com/image.png")
        assert resolver.is_external("//example.com/image.png")
        assert not resolver.is_external("image.png")
        assert not resolver.is_external("/images/test.png")

    def test_resolve_absolute_path(
        self, resolver: HexoResolver, context: CheckContext, tmp_path: Path
    ) -> None:
        """测试绝对路径解析"""
        source_file = tmp_path / "_posts" / "test.md"

        resolved = resolver.resolve("/images/test.png", source_file, context)
        assert resolved == tmp_path / "images" / "test.png"

    def test_resolve_relative_path_in_post(
        self, resolver: HexoResolver, context: CheckContext, tmp_path: Path
    ) -> None:
        """测试文章中相对路径解析（资源文件夹）"""
        # 创建文章和资源文件夹
        source_file = tmp_path / "_posts" / "2024-01-01-test.md"
        source_file.write_text("test", encoding="utf-8")

        asset_folder = tmp_path / "_posts" / "2024-01-01-test"
        asset_folder.mkdir()
        (asset_folder / "image.png").write_bytes(b"fake")

        resolved = resolver.resolve("image.png", source_file, context)
        assert resolved == asset_folder / "image.png"

    def test_resolve_relative_path_in_page(
        self, resolver: HexoResolver, context: CheckContext, tmp_path: Path
    ) -> None:
        """测试页面中相对路径解析"""
        source_file = tmp_path / "pages" / "about.md"
        source_file.parent.mkdir(parents=True, exist_ok=True)

        resolved = resolver.resolve("image.png", source_file, context)
        assert resolved == tmp_path / "pages" / "image.png"

    def test_exists_in_asset_folder(
        self, resolver: HexoResolver, context: CheckContext, tmp_path: Path
    ) -> None:
        """测试资源文件夹中文件存在性"""
        source_file = tmp_path / "_posts" / "2024-01-01-test.md"

        asset_folder = tmp_path / "_posts" / "2024-01-01-test"
        asset_folder.mkdir()
        (asset_folder / "exists.png").write_bytes(b"fake")

        assert resolver.exists("exists.png", source_file, context)
        assert not resolver.exists("missing.png", source_file, context)

    def test_exists_external(
        self,
        resolver: HexoResolver,
        context: CheckContext,
        tmp_path: Path,
    ) -> None:
        """测试外部链接始终返回 True"""
        source_file = tmp_path / "_posts" / "test.md"

        assert resolver.exists("https://example.com/image.png", source_file, context)

    def test_normalize_path_url_encoding(self, resolver: HexoResolver) -> None:
        """测试 URL 编码路径规范化"""
        assert resolver._normalize_path("path%20with%20space.png") == "path with space.png"
        assert resolver._normalize_path("./relative.png") == "relative.png"
        # 注意：_normalize_path 不处理前后空格，这由 resolve() 在调用前使用 strip() 处理
        assert resolver._normalize_path("normal.png") == "normal.png"

    def test_find_similar(
        self, resolver: HexoResolver, context: CheckContext, tmp_path: Path
    ) -> None:
        """测试相似路径查找"""
        source_file = tmp_path / "_posts" / "2024-01-01-test.md"

        asset_folder = tmp_path / "_posts" / "2024-01-01-test"
        asset_folder.mkdir()
        (asset_folder / "screenshot.png").write_bytes(b"fake")

        # 查找 screnshot.png（拼写错误）的相似项
        similar = resolver.find_similar("screnshot.png", source_file, context, threshold=0.6)
        assert len(similar) > 0
        assert "screenshot.png" in similar

    def test_is_post_file(
        self, resolver: HexoResolver, context: CheckContext, tmp_path: Path
    ) -> None:
        """测试文章文件判断"""
        post_file = tmp_path / "_posts" / "test.md"
        page_file = tmp_path / "pages" / "about.md"

        assert resolver._is_post_file(post_file, context)
        assert not resolver._is_post_file(page_file, context)
