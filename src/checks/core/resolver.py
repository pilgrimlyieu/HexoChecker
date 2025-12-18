"""PathResolver - 路径解析器抽象基类"""

from __future__ import annotations

from abc import ABC, abstractmethod
from difflib import get_close_matches
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from checks.core.context import CheckContext


class PathResolver(ABC):
    """路径解析器抽象基类

    负责将文档中的相对路径解析为实际文件路径，
    并提供路径存在性检查和相似路径查找功能。

    不同的项目结构（如 Hexo、Hugo、Jekyll）可以实现
    自己的解析器来处理特定的路径规则。
    """

    name: str = "base"
    description: str = "Base path resolver"

    @abstractmethod
    def resolve(self, path: str, source_file: Path, ctx: CheckContext) -> Path | None:
        """解析相对路径为绝对路径

        Args:
            path: 文档中的路径字符串
            source_file: 引用此路径的源文件
            ctx: 检查上下文

        Returns:
            解析后的绝对路径，无法解析时返回 None
        """
        ...

    @abstractmethod
    def exists(self, path: str, source_file: Path, ctx: CheckContext) -> bool:
        """检查路径指向的资源是否存在

        Args:
            path: 文档中的路径字符串
            source_file: 引用此路径的源文件
            ctx: 检查上下文

        Returns:
            资源是否存在
        """
        ...

    def is_external(self, path: str) -> bool:
        """判断是否为外部链接

        Args:
            path: 路径字符串

        Returns:
            是否为外部链接（http/https）
        """
        return path.startswith(("http://", "https://", "//"))

    def find_similar(
        self, path: str, source_file: Path, ctx: CheckContext, threshold: float = 0.6
    ) -> list[str]:
        """查找相似路径（用于修复建议）

        默认实现使用 difflib 进行模糊匹配。
        子类可以覆盖此方法提供更智能的建议。

        Args:
            path: 原始路径
            source_file: 源文件
            ctx: 检查上下文
            threshold: 相似度阈值 (0-1)

        Returns:
            相似路径列表，按相似度降序排列
        """
        resolved = self.resolve(path, source_file, ctx)
        if resolved is None:
            return []

        # 获取目标目录
        target_dir = resolved.parent
        if not target_dir.exists():
            # 目录不存在，尝试在父目录中查找相似目录
            parent = target_dir.parent
            if parent.exists():
                similar_dirs = get_close_matches(
                    target_dir.name,
                    [d.name for d in parent.iterdir() if d.is_dir()],
                    n=1,
                    cutoff=threshold,
                )
                if similar_dirs:
                    target_dir = parent / similar_dirs[0]

        if not target_dir.exists():
            return []

        # 在目录中查找相似文件
        target_name = resolved.name
        candidates = [f.name for f in target_dir.iterdir() if f.is_file()]
        similar_files = get_close_matches(target_name, candidates, n=3, cutoff=threshold)

        # 构建相对路径
        result = []
        for similar in similar_files:
            similar_path = target_dir / similar
            try:
                # 尝试获取相对于源文件目录的路径
                rel_path = similar_path.relative_to(source_file.parent)
                result.append(rel_path.as_posix())
            except ValueError:
                # 如果无法获取相对路径，使用绝对路径
                result.append(similar_path.as_posix())

        return result

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"
