"""HexoResolver - Hexo 博客路径解析器"""

from dataclasses import dataclass, field
from difflib import get_close_matches
from pathlib import Path
from urllib.parse import unquote

from checks.core.context import CheckContext
from checks.core.resolver import PathResolver


@dataclass
class HexoResolver(PathResolver):
    """Hexo 博客路径解析器

    处理 Hexo 特有的路径规则：
    - _posts 目录下的文章可以直接引用同名资源文件夹中的文件
    - 例如：_posts/2024-01-01-hello.md 可以用 image.png
      引用 _posts/2024-01-01-hello/image.png

    Attributes:
        post_dir: 文章目录名列表（默认 ["_posts"]）
        asset_folder_per_post: 是否启用文章资源文件夹
        pages: 普通页面目录列表
    """

    name: str = "hexo"
    description: str = "Hexo blog path resolver"

    post_dir: list[str] = field(default_factory=lambda: ["_posts"])
    asset_folder_per_post: bool = True
    pages: list[str] = field(default_factory=list)

    def _normalize_path(self, path: str) -> str:
        """规范化路径：解码 URL 编码、去除 ./ 前缀"""
        # 解码 URL 编码（如 %20 -> 空格）
        path = unquote(path)
        # 去除 ./ 前缀
        if path.startswith("./"):
            path = path[2:]
        return path

    def resolve(self, path: str, source_file: Path, ctx: CheckContext) -> Path | None:
        """解析路径（Hexo 规则）"""
        if self.is_external(path):
            return None

        path = self._normalize_path(path.strip())

        # 绝对路径（相对于项目根目录）
        if path.startswith("/"):
            return ctx.root / path[1:]

        # 检查是否在 _posts 目录中
        if self._is_post_file(source_file, ctx) and self.asset_folder_per_post:
            # 尝试在同名资源文件夹中查找
            asset_folder = source_file.parent / source_file.stem
            asset_path = asset_folder / path
            if asset_path.exists():
                return asset_path

        # 默认：相对于源文件目录
        return source_file.parent / path

    def exists(self, path: str, source_file: Path, ctx: CheckContext) -> bool:
        """检查路径是否存在"""
        if self.is_external(path):
            return True

        resolved = self.resolve(path, source_file, ctx)
        return resolved is not None and resolved.exists()

    def find_similar(
        self, path: str, source_file: Path, ctx: CheckContext, threshold: float = 0.6
    ) -> list[str]:
        """查找相似路径（Hexo 增强版）"""
        results: list[str] = []

        # 解析目标目录和文件名
        path_obj = Path(path)
        target_name = path_obj.name
        target_dir_parts = path_obj.parts[:-1] if len(path_obj.parts) > 1 else ()

        # 确定搜索目录列表
        search_dirs: list[Path] = []

        # 1. 源文件所在目录
        base_dir = source_file.parent
        if target_dir_parts:
            search_dirs.append(base_dir / Path(*target_dir_parts))
        else:
            search_dirs.append(base_dir)

        # 2. 如果是 post，添加同名资源文件夹
        if self._is_post_file(source_file, ctx) and self.asset_folder_per_post:
            asset_folder = source_file.parent / source_file.stem
            if target_dir_parts:
                search_dirs.append(asset_folder / Path(*target_dir_parts))
            else:
                search_dirs.append(asset_folder)

        # 在各目录中搜索
        for search_dir in search_dirs:
            similar = self._find_similar_in_dir(
                search_dir, target_name, target_dir_parts, source_file, ctx, threshold
            )
            results.extend(similar)

        # 去重并返回
        seen = set()
        unique_results = []
        for r in results:
            if r not in seen:
                seen.add(r)
                unique_results.append(r)

        return unique_results

    def _find_similar_in_dir(
        self,
        search_dir: Path,
        target_name: str,
        target_dir_parts: tuple,
        source_file: Path,
        ctx: CheckContext,
        threshold: float,
    ) -> list[str]:
        """在指定目录中查找相似文件"""
        results = []

        # 目录不存在时，尝试查找相似目录
        if not search_dir.exists():
            parent = search_dir.parent
            if parent.exists() and target_dir_parts:
                similar_dirs = get_close_matches(
                    search_dir.name,
                    [d.name for d in parent.iterdir() if d.is_dir()],
                    n=1,
                    cutoff=threshold,
                )
                if similar_dirs:
                    search_dir = parent / similar_dirs[0]

        if not search_dir.exists():
            return results

        # 查找相似文件
        candidates = [f.name for f in search_dir.iterdir() if f.is_file()]
        similar_files = get_close_matches(target_name, candidates, n=3, cutoff=threshold)

        # 构建结果路径
        for similar in similar_files:
            similar_path = search_dir / similar

            # 尝试构建相对路径
            # 对于 post 的资源文件夹，直接用文件名
            if self._is_post_file(source_file, ctx) and self.asset_folder_per_post:
                asset_folder = source_file.parent / source_file.stem
                if similar_path.is_relative_to(asset_folder):
                    try:
                        rel = similar_path.relative_to(asset_folder)
                        results.append(rel.as_posix())
                        continue
                    except ValueError:
                        pass

            # 否则用相对于源文件目录的路径
            try:
                rel = similar_path.relative_to(source_file.parent)
                results.append(rel.as_posix())
            except ValueError:
                # 无法获取相对路径时使用绝对路径
                try:
                    rel = similar_path.relative_to(ctx.root)
                    results.append("/" + rel.as_posix())
                except ValueError:
                    results.append(similar_path.as_posix())

        return results

    def _is_post_file(self, file: Path, ctx: CheckContext) -> bool:
        """判断文件是否在 _posts 目录中"""
        try:
            rel_path = file.relative_to(ctx.root)
            parts = rel_path.parts
            return len(parts) > 0 and parts[0] in self.post_dir
        except ValueError:
            return False
