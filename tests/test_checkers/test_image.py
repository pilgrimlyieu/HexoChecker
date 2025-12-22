"""Tests for ImageChecker"""

from pathlib import Path

import pytest

from checks import CheckContext, Config, ImageChecker
from checks.checkers.image import ImagePatterns
from checks.resolvers import DefaultResolver, HexoResolver


class TestImagePatterns:
    """ImagePatterns 正则表达式测试"""

    def test_markdown_simple(self) -> None:
        """测试简单 Markdown 图片"""
        match = ImagePatterns.MARKDOWN_IMAGE.search("![alt](image.png)")
        assert match is not None
        assert match.group("path_normal") == "image.png"

    def test_markdown_with_title(self) -> None:
        """测试带标题的 Markdown 图片"""
        match = ImagePatterns.MARKDOWN_IMAGE.search('![alt](image.png "title")')
        assert match is not None
        assert match.group("path_normal") == "image.png"

    def test_markdown_nested_parens(self) -> None:
        """测试嵌套括号的路径"""
        match = ImagePatterns.MARKDOWN_IMAGE.search("![](image(1).png)")
        assert match is not None
        assert match.group("path_normal") == "image(1).png"

    def test_markdown_angle_brackets(self) -> None:
        """测试尖括号包裹的路径"""
        match = ImagePatterns.MARKDOWN_IMAGE.search("![](<path with spaces.png>)")
        assert match is not None
        assert match.group("path_angle") == "path with spaces.png"

    def test_markdown_nested_alt(self) -> None:
        """测试嵌套方括号的 alt 文本"""
        match = ImagePatterns.MARKDOWN_IMAGE.search("![[nested] alt](image.png)")
        assert match is not None
        assert match.group("path_normal") == "image.png"

    def test_html_img_basic(self) -> None:
        """测试基本 HTML img 标签"""
        match = ImagePatterns.HTML_IMG.search('<img src="image.png">')
        assert match is not None
        assert match.group("path") == "image.png"

    def test_html_img_with_attributes(self) -> None:
        """测试带其他属性的 img 标签"""
        match = ImagePatterns.HTML_IMG.search('<img alt="test" src="image.png" width="100">')
        assert match is not None
        assert match.group("path") == "image.png"

    def test_html_img_self_closing(self) -> None:
        """测试自闭合 img 标签"""
        match = ImagePatterns.HTML_IMG.search('<img src="image.png" />')
        assert match is not None
        assert match.group("path") == "image.png"

    def test_html_img_single_quotes(self) -> None:
        """测试单引号"""
        match = ImagePatterns.HTML_IMG.search("<img src='image.png'>")
        assert match is not None
        assert match.group("path") == "image.png"

    def test_code_fence_detection(self) -> None:
        """测试代码块检测"""
        assert ImagePatterns.CODE_FENCE.match("```python")
        assert ImagePatterns.CODE_FENCE.match("```")
        assert ImagePatterns.CODE_FENCE.match("  ```")  # 缩进
        assert not ImagePatterns.CODE_FENCE.match("text ```")

    def test_inline_code_detection(self) -> None:
        """测试行内代码检测"""
        text = "Some `inline code` here"
        result = ImagePatterns.INLINE_CODE.sub("", text)
        assert result == "Some  here"


class TestImageChecker:
    """ImageChecker 测试"""

    @pytest.fixture
    def checker(self) -> ImageChecker:
        """创建检查器实例"""
        return ImageChecker()

    @pytest.fixture
    def context(self, tmp_path: Path) -> CheckContext:
        """创建检查上下文"""
        resolver = DefaultResolver()
        config = Config(root=tmp_path, resolver=resolver)
        return CheckContext(root=tmp_path, config=config, resolver=resolver)

    def test_check_valid_image(
        self, checker: ImageChecker, context: CheckContext, tmp_path: Path
    ) -> None:
        """测试有效图片不产生 issue"""
        # 创建文件
        md_file = tmp_path / "test.md"
        md_file.write_text("![Test](image.png)", encoding="utf-8")
        (tmp_path / "image.png").write_bytes(b"fake")

        issues = checker.check(md_file, md_file.read_text(), context)
        assert len(issues) == 0

    def test_check_missing_image(
        self, checker: ImageChecker, context: CheckContext, tmp_path: Path
    ) -> None:
        """测试缺失图片产生 issue"""
        md_file = tmp_path / "test.md"
        md_file.write_text("![Test](missing.png)", encoding="utf-8")

        issues = checker.check(md_file, md_file.read_text(), context)
        assert len(issues) == 1
        assert issues[0].type == "broken_image"
        assert "missing.png" in issues[0].message

    def test_skip_external_links(
        self, checker: ImageChecker, context: CheckContext, tmp_path: Path
    ) -> None:
        """测试跳过外部链接"""
        md_file = tmp_path / "test.md"
        content = """
![HTTP](https://example.com/image.png)
![HTTPS](https://example.com/image.png)
![Protocol Relative](//example.com/image.png)
"""
        md_file.write_text(content, encoding="utf-8")

        issues = checker.check(md_file, content, context)
        assert len(issues) == 0

    def test_skip_code_blocks(
        self, checker: ImageChecker, context: CheckContext, tmp_path: Path
    ) -> None:
        """测试跳过代码块"""
        md_file = tmp_path / "test.md"
        content = """
```markdown
![Should Skip](nonexistent.png)
```
"""
        md_file.write_text(content, encoding="utf-8")

        issues = checker.check(md_file, content, context)
        assert len(issues) == 0

    def test_skip_inline_code(
        self, checker: ImageChecker, context: CheckContext, tmp_path: Path
    ) -> None:
        """测试跳过行内代码"""
        md_file = tmp_path / "test.md"
        content = "Use `![Image](path.png)` syntax for images"
        md_file.write_text(content, encoding="utf-8")

        issues = checker.check(md_file, content, context)
        assert len(issues) == 0

    def test_check_html_img(
        self, checker: ImageChecker, context: CheckContext, tmp_path: Path
    ) -> None:
        """测试 HTML img 标签"""
        md_file = tmp_path / "test.md"
        content = '<img src="missing.png" alt="test">'
        md_file.write_text(content, encoding="utf-8")

        issues = checker.check(md_file, content, context)
        assert len(issues) == 1

    def test_multiple_issues_same_line(
        self, checker: ImageChecker, context: CheckContext, tmp_path: Path
    ) -> None:
        """测试同一行多个问题"""
        md_file = tmp_path / "test.md"
        content = "![A](a.png) ![B](b.png)"
        md_file.write_text(content, encoding="utf-8")

        issues = checker.check(md_file, content, context)
        assert len(issues) == 2

    def test_supports_file(self, checker: ImageChecker) -> None:
        """测试文件类型支持"""
        assert checker.supports_file(Path("test.md"))
        assert checker.supports_file(Path("test.markdown"))
        assert checker.supports_file(Path("test.mdx"))
        assert not checker.supports_file(Path("test.txt"))
        assert not checker.supports_file(Path("test.py"))


class TestImageCheckerWithHexo:
    """ImageChecker + HexoResolver 集成测试"""

    @pytest.fixture
    def hexo_context(self, tmp_path: Path) -> CheckContext:
        """创建 Hexo 检查上下文"""
        resolver = HexoResolver(post_dir=["_posts"], asset_folder_per_post=True)
        config = Config(root=tmp_path, resolver=resolver)
        (tmp_path / "_posts").mkdir()
        return CheckContext(root=tmp_path, config=config, resolver=resolver)

    def test_hexo_asset_folder(self, hexo_context: CheckContext) -> None:
        """测试 Hexo 资源文件夹"""
        tmp_path = hexo_context.root

        # 创建文章和资源文件夹
        md_file = tmp_path / "_posts" / "2024-01-01-test.md"
        md_file.write_text("![Image](test.png)", encoding="utf-8")

        asset_folder = tmp_path / "_posts" / "2024-01-01-test"
        asset_folder.mkdir()
        (asset_folder / "test.png").write_bytes(b"fake")

        checker = ImageChecker()
        issues = checker.check(md_file, md_file.read_text(), hexo_context)
        assert len(issues) == 0

    def test_hexo_missing_asset(self, hexo_context: CheckContext) -> None:
        """测试 Hexo 缺失资源"""
        tmp_path = hexo_context.root

        md_file = tmp_path / "_posts" / "2024-01-01-test.md"
        md_file.write_text("![Image](missing.png)", encoding="utf-8")

        checker = ImageChecker()
        issues = checker.check(md_file, md_file.read_text(), hexo_context)
        assert len(issues) == 1
