"""DefaultResolver - 默认路径解析器"""

from pathlib import Path

from checks.core.context import CheckContext
from checks.core.resolver import PathResolver


class DefaultResolver(PathResolver):
    """默认路径解析器

    简单的路径解析：
    - 绝对路径（以 / 开头）相对于项目根目录
    - 相对路径相对于源文件所在目录
    """

    name = "default"
    description = "Default path resolver"

    def resolve(self, path: str, source_file: Path, ctx: CheckContext) -> Path | None:
        """解析路径"""
        if self.is_external(path):
            return None

        path = path.strip()

        # 绝对路径（相对于项目根目录）
        if path.startswith("/"):
            return ctx.root / path[1:]

        # 相对路径（相对于源文件目录）
        return source_file.parent / path

    def exists(self, path: str, source_file: Path, ctx: CheckContext) -> bool:
        """检查路径是否存在"""
        if self.is_external(path):
            return True  # 外部链接假定存在

        resolved = self.resolve(path, source_file, ctx)
        return resolved is not None and resolved.exists()
