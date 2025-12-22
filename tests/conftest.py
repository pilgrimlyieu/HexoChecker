"""Pytest 配置和共享 fixtures"""

from pathlib import Path

import pytest

from checks import CheckContext, Config, ImageChecker
from checks.resolvers import DefaultResolver, HexoResolver


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """创建临时项目目录结构"""
    # 创建基础目录
    (tmp_path / "_posts").mkdir()
    (tmp_path / "pages").mkdir()
    (tmp_path / "images").mkdir()

    return tmp_path


@pytest.fixture
def sample_md_file(tmp_project: Path) -> Path:
    """创建示例 Markdown 文件"""
    md_file = tmp_project / "_posts" / "2024-01-01-test.md"
    md_file.write_text(
        """---
title: Test Post
---

# Test Post

This is a test post with images.

![Valid Image](test.png)
![Missing Image](missing.png)

Some more content.
""",
        encoding="utf-8",
    )

    # 创建对应的资源文件夹和图片
    asset_folder = tmp_project / "_posts" / "2024-01-01-test"
    asset_folder.mkdir()
    (asset_folder / "test.png").write_bytes(b"fake png")

    return md_file


@pytest.fixture
def default_resolver() -> DefaultResolver:
    """默认路径解析器"""
    return DefaultResolver()


@pytest.fixture
def hexo_resolver() -> HexoResolver:
    """Hexo 路径解析器"""
    return HexoResolver(
        post_dir=["_posts"],
        asset_folder_per_post=True,
    )


@pytest.fixture
def default_config(default_resolver: DefaultResolver) -> Config:
    """默认配置"""
    return Config(
        root=".",
        include=["**/*.md"],
        resolver=default_resolver,
        checkers=[ImageChecker()],
    )


@pytest.fixture
def hexo_config(hexo_resolver: HexoResolver) -> Config:
    """Hexo 配置"""
    return Config(
        root=".",
        include=["_posts/**/*.md", "pages/**/*.md"],
        resolver=hexo_resolver,
        checkers=[ImageChecker()],
    )


@pytest.fixture
def check_context(tmp_project: Path, hexo_config: Config) -> CheckContext:
    """检查上下文"""
    assert hexo_config.resolver is not None
    return CheckContext(
        root=tmp_project,
        config=hexo_config,
        resolver=hexo_config.resolver,
    )


# ============================================================================
# 测试数据 fixtures
# ============================================================================


@pytest.fixture
def markdown_with_images() -> str:
    """包含各种图片语法的 Markdown 内容"""
    return """# Test Document

## Basic Images

![Simple](image.png)
![With Title](image.png "Image Title")
![With Alt Text](path/to/image.jpg)

## Complex Paths

![Nested Parens](image(1).png)
![URL Encoded](path%20with%20space.png)
![Absolute](/images/absolute.png)

## HTML Images

<img src="html-image.png" alt="HTML">
<img alt="Reversed" src="reversed.png">
<img src="self-closing.png" />

## Code Blocks (should be skipped)

```markdown
![Code Block Image](should-skip.png)
```

Inline `![code](skip.png)` should also skip.

## External Links (should be skipped)

![External](https://example.com/image.png)
![Protocol Relative](//example.com/image.png)
"""


@pytest.fixture
def markdown_simple() -> str:
    """简单的 Markdown 内容"""
    return """# Simple Test

![Test Image](test.png)

End of file.
"""
