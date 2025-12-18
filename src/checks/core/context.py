"""CheckContext - 检查上下文"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from checks.core.issue import ContextLines

if TYPE_CHECKING:
    from checks.config import Config
    from checks.core.resolver import PathResolver


@dataclass
class CheckContext:
    """检查过程的上下文信息

    在检查过程中传递给检查器，提供配置、路径解析器、
    文件缓存等共享资源。

    Attributes:
        root: 项目根目录
        config: 配置对象
        resolver: 路径解析器
        file_cache: 文件内容缓存
    """

    root: Path
    config: Config
    resolver: PathResolver
    file_cache: dict[Path, str] = field(default_factory=dict)

    def __post_init__(self):
        """确保 root 是绝对路径"""
        self.root = Path(self.root).resolve()

    def read_file(self, path: Path) -> str:
        """读取文件内容（带缓存）

        Args:
            path: 文件路径

        Returns:
            文件内容

        Raises:
            FileNotFoundError: 文件不存在
            UnicodeDecodeError: 编码错误
        """
        path = Path(path).resolve()

        if path not in self.file_cache:
            self.file_cache[path] = path.read_text(encoding="utf-8")

        return self.file_cache[path]

    def get_file_lines(self, path: Path) -> list[str]:
        """获取文件所有行

        Args:
            path: 文件路径

        Returns:
            行列表（不含换行符）
        """
        content = self.read_file(path)
        return content.splitlines()

    def get_context_lines(
        self, file: Path, line: int, before: int = 3, after: int = 3
    ) -> ContextLines:
        """获取指定行的上下文

        Args:
            file: 文件路径
            line: 目标行号（1-based）
            before: 前面的行数
            after: 后面的行数

        Returns:
            ContextLines 对象
        """
        lines = self.get_file_lines(file)
        line_idx = line - 1  # 转换为 0-based

        # 计算范围
        start = max(0, line_idx - before)
        end = min(len(lines), line_idx + after + 1)

        # 构建上下文
        before_lines = [(i + 1, lines[i]) for i in range(start, line_idx)]
        current_line = (line, lines[line_idx] if line_idx < len(lines) else "")
        after_lines = [(i + 1, lines[i]) for i in range(line_idx + 1, end)]

        return ContextLines(before=before_lines, current=current_line, after=after_lines)

    def relative_path(self, path: Path) -> Path:
        """获取相对于项目根目录的路径

        Args:
            path: 文件路径

        Returns:
            相对路径，如果不在项目内则返回原路径
        """
        try:
            return path.resolve().relative_to(self.root)
        except ValueError:
            return path

    def clear_cache(self):
        """清空文件缓存"""
        self.file_cache.clear()
