"""ImageChecker - 图片路径检查器"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from pathlib import Path

    from checks.core.context import CheckContext

from checks.core.checker import Checker
from checks.core.issue import Issue, Severity


# 预编译的正则表达式模式
class ImagePatterns:
    """图片匹配正则表达式集合

    使用更健壮的正则表达式，支持：
    - 嵌套括号: ![](path(1).png)
    - 带空格的路径（引号包裹）: ![]("path with space.png")
    - 带标题: ![](path.png "title")
    - HTML 多种属性顺序
    """

    # Markdown 图片 - 支持嵌套括号和复杂路径
    # ![alt](path) 或 ![alt](path "title") 或 ![alt](<path with spaces>)
    MARKDOWN_IMAGE: ClassVar[re.Pattern[str]] = re.compile(
        r"!\[(?:[^\[\]]|\[[^\]]*\])*\]\("  # ![alt]( - alt 支持嵌套方括号
        r"(?:"
        r"<(?P<path_angle>[^>]+)>"  # <path> 尖括号包裹的路径
        r"|"
        r'(?P<path_normal>(?:[^()\s"]|\([^()]*\))+)'  # 普通路径，支持嵌套括号
        r")"
        r'(?:\s+["\'][^"\']*["\'])?'  # 可选的标题
        r"\)",
        re.MULTILINE,
    )

    # HTML img 标签 - 更宽松的匹配
    HTML_IMG: ClassVar[re.Pattern[str]] = re.compile(
        r"<img\s+"  # <img 开头
        r"(?:[^>]*?\s+)?"  # 其他属性
        r'src=["\'](?P<path>[^"\']+)["\']'  # src 属性
        r"[^>]*"  # 剩余属性
        r"/?>",  # 结束
        re.IGNORECASE,
    )

    # HTML video poster
    HTML_VIDEO_POSTER: ClassVar[re.Pattern[str]] = re.compile(
        r"<video\s+"
        r"(?:[^>]*?\s+)?"
        r'poster=["\'](?P<path>[^"\']+)["\']'
        r"[^>]*"
        r">",
        re.IGNORECASE,
    )

    # 代码块（支持缩进）
    CODE_FENCE: ClassVar[re.Pattern[str]] = re.compile(r"^\s*```")

    # 行内代码（用于跳过）
    INLINE_CODE: ClassVar[re.Pattern[str]] = re.compile(r"`[^`]+`")

    # 路径清理模式
    PATH_SUFFIX: ClassVar[re.Pattern[str]] = re.compile(r"#[\w-]+$")


@dataclass
class ImageChecker(Checker):
    """图片路径检查器

    检查 Markdown 和 HTML 中的图片路径是否有效。
    支持模糊匹配以提供修复建议。

    Attributes:
        ignore_external: 是否忽略外部链接
        fuzzy_threshold: 模糊匹配阈值
        skip_code_blocks: 是否跳过代码块中的内容
        skip_inline_code: 是否跳过行内代码
        check_html_img: 是否检查 HTML img 标签
        check_video_poster: 是否检查 video poster 属性
    """

    name: str = "image"
    description: str = "Check image paths in Markdown and HTML"

    ignore_external: bool = True
    fuzzy_threshold: float = 0.6
    skip_code_blocks: bool = True
    skip_inline_code: bool = True
    check_html_img: bool = True
    check_video_poster: bool = True

    def check(
        self,
        file: Path,
        content: str,
        ctx: CheckContext,
    ) -> list[Issue]:
        """检查文件中的图片路径"""
        issues: list[Issue] = []
        lines = content.splitlines()

        # 跟踪代码块状态
        in_code_block = False

        for line_num, line in enumerate(lines, 1):
            # 检测代码块边界
            if self.skip_code_blocks and ImagePatterns.CODE_FENCE.match(line):
                in_code_block = not in_code_block
                continue

            # 跳过代码块内容
            if in_code_block:
                continue

            # 处理行内代码（替换为占位符以避免匹配）
            check_line = line
            if self.skip_inline_code:
                check_line = ImagePatterns.INLINE_CODE.sub("", line)

            # 检查 Markdown 图片
            issues.extend(self._check_markdown_images(check_line, line, file, line_num, ctx))

            # 检查 HTML img 标签
            if self.check_html_img:
                issues.extend(self._check_html_images(check_line, line, file, line_num, ctx))

            # 检查 video poster
            if self.check_video_poster:
                issues.extend(self._check_video_poster(check_line, line, file, line_num, ctx))

        return issues

    def _check_markdown_images(
        self,
        check_line: str,
        original_line: str,
        file: Path,
        line_num: int,
        ctx: CheckContext,
    ) -> list[Issue]:
        """检查 Markdown 图片语法"""
        issues: list[Issue] = []

        for match in ImagePatterns.MARKDOWN_IMAGE.finditer(check_line):
            # 获取路径（优先尖括号内的路径）
            path = match.group("path_angle") or match.group("path_normal")
            if not path:
                continue

            # 在原始行中查找位置
            column = original_line.find(path)

            issue = self._check_path(
                path=path,
                file=file,
                line=line_num,
                column=column if column >= 0 else match.start(),
                line_content=original_line,
                ctx=ctx,
            )
            if issue:
                issues.append(issue)

        return issues

    def _check_pattern_matches(
        self,
        pattern: re.Pattern[str],
        check_line: str,
        original_line: str,
        file: Path,
        line_num: int,
        ctx: CheckContext,
    ) -> list[Issue]:
        """检查正则匹配的路径

        通用方法，用于检查 HTML img、video poster 等模式。
        """
        issues: list[Issue] = []

        for match in pattern.finditer(check_line):
            path = match.group("path")
            column = original_line.find(path)

            issue = self._check_path(
                path=path,
                file=file,
                line=line_num,
                column=column if column >= 0 else match.start("path"),
                line_content=original_line,
                ctx=ctx,
            )
            if issue:
                issues.append(issue)

        return issues

    def _check_html_images(
        self,
        check_line: str,
        original_line: str,
        file: Path,
        line_num: int,
        ctx: CheckContext,
    ) -> list[Issue]:
        """检查 HTML img 标签"""
        return self._check_pattern_matches(
            ImagePatterns.HTML_IMG, check_line, original_line, file, line_num, ctx
        )

    def _check_video_poster(
        self,
        check_line: str,
        original_line: str,
        file: Path,
        line_num: int,
        ctx: CheckContext,
    ) -> list[Issue]:
        """检查 video poster 属性"""
        return self._check_pattern_matches(
            ImagePatterns.HTML_VIDEO_POSTER, check_line, original_line, file, line_num, ctx
        )

    def _check_path(
        self,
        path: str,
        file: Path,
        line: int,
        column: int,
        line_content: str,
        ctx: CheckContext,
    ) -> Issue | None:
        """检查单个路径"""
        # 清理路径（去除锚点等）
        clean_path = self._clean_path(path)

        # 检查是否为外部链接
        if self.ignore_external and ctx.resolver.is_external(clean_path):
            return None

        # 检查路径是否存在
        if ctx.resolver.exists(clean_path, file, ctx):
            return None

        # 路径不存在，创建 Issue
        suggestion = self._find_suggestion(clean_path, file, ctx)

        return Issue(
            file=file,
            line=line,
            column=column,
            type="broken_image",
            message=f"Image not found: `{clean_path}`",
            original=path,
            suggestion=suggestion,
            severity=Severity.ERROR,
            checker=self.name,
            metadata={
                "clean_path": clean_path,
                "line_content": line_content,
            },
        )

    def _clean_path(self, path: str) -> str:
        """清理路径字符串

        移除：
        - URL 锚点 (#section)
        - 尾随空格
        """
        path = path.strip()
        path = ImagePatterns.PATH_SUFFIX.sub("", path)
        return path

    def _find_suggestion(
        self,
        path: str,
        file: Path,
        ctx: CheckContext,
    ) -> str | None:
        """查找修复建议"""
        similar = ctx.resolver.find_similar(
            path,
            file,
            ctx,
            threshold=self.fuzzy_threshold,
        )
        return similar[0] if similar else None

    def supports_file(self, file: Path) -> bool:
        """只检查 Markdown 文件"""
        return file.suffix.lower() in (".md", ".markdown", ".mdx")
