"""PatchFixer - 基于 Patch 文件的修复器"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from checks.fixers.base import FixAction, Fixer, FixResult, FixSession

if TYPE_CHECKING:
    from checks.core.issue import Issue


@dataclass
class PatchFixer(Fixer):
    """基于 Patch 文件的修复器

    生成 unified diff 格式的 patch 文件，支持：
    - 修复预览（dry-run）
    - Patch 文件保存
    - 撤销修复（通过 patch -R）

    Attributes:
        patch_dir: Patch 文件存储目录
        context_lines: Diff 上下文行数
    """

    name: str = "patch"
    description: str = "Patch-based fixer with undo support"

    patch_dir: Path = field(default_factory=lambda: Path(".checks/patches"))
    context_lines: int = 3

    def fix(self, issues: list[Issue], root: Path, dry_run: bool = False) -> FixSession:
        """执行修复（生成 patch）"""
        session = FixSession()

        # 过滤可修复的问题
        fixable = self.filter_fixable(issues)
        if not fixable:
            session.complete()
            return session

        # 按文件分组
        by_file: dict[Path, list[Issue]] = {}
        for issue in fixable:
            by_file.setdefault(issue.file, []).append(issue)

        # 为每个文件生成修复
        all_patches: list[str] = []
        for file, file_issues in by_file.items():
            patch, results = self._fix_file(file, file_issues, root)
            if patch:
                all_patches.append(patch)
            session.results.extend(results)

        # 保存 patch 文件
        if all_patches and not dry_run:
            combined_patch = "\n".join(all_patches)
            patch_file = self._save_patch(combined_patch, session.id, root)

            # 应用 patch
            self._apply_patch(patch_file, root)

            # 标记为已应用
            for result in session.results:
                if result.action == FixAction.ACCEPT:
                    result.applied = True

        session.complete()
        return session

    def _fix_file(
        self, file: Path, issues: list[Issue], root: Path
    ) -> tuple[str | None, list[FixResult]]:
        """修复单个文件的所有问题"""
        results: list[FixResult] = []

        # 读取原始内容
        try:
            original_content = file.read_text(encoding="utf-8")
        except Exception as e:
            for issue in issues:
                results.append(
                    FixResult(issue=issue, action=FixAction.SKIP, error=f"Failed to read file: {e}")
                )
            return None, results

        # 按行号降序排序（从后往前修复，避免行号偏移）
        issues = sorted(issues, key=lambda i: i.line, reverse=True)

        # 应用修复
        lines = original_content.splitlines(keepends=True)

        # 确保最后一行有换行符
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"

        for issue in issues:
            fix = issue.get_fix()
            if not fix:
                results.append(
                    FixResult(issue=issue, action=FixAction.SKIP, error="No fix available")
                )
                continue

            # 应用修复到行
            line_idx = issue.line - 1
            if 0 <= line_idx < len(lines):
                original_line = lines[line_idx]
                new_line = fix.apply_to_line(original_line)
                lines[line_idx] = new_line

                results.append(
                    FixResult(
                        issue=issue,
                        action=FixAction.ACCEPT,
                        fix=fix,
                    )
                )
            else:
                results.append(
                    FixResult(
                        issue=issue, action=FixAction.SKIP, error=f"Line {issue.line} out of range"
                    )
                )

        # 生成 diff
        fixed_content = "".join(lines)
        if original_content == fixed_content:
            return None, results

        # 获取相对路径
        try:
            rel_path = file.relative_to(root)
        except ValueError:
            rel_path = file

        diff = difflib.unified_diff(
            original_content.splitlines(keepends=True),
            fixed_content.splitlines(keepends=True),
            fromfile=f"a/{rel_path.as_posix()}",
            tofile=f"b/{rel_path.as_posix()}",
            n=self.context_lines,
        )

        return "".join(diff), results

    def _save_patch(self, patch: str, session_id: str, root: Path) -> Path:
        """保存 patch 文件"""
        patch_dir = root / self.patch_dir
        patch_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        patch_file = patch_dir / f"{timestamp}_{session_id}.patch"
        patch_file.write_text(patch, encoding="utf-8")

        return patch_file

    def _apply_patch(self, patch_file: Path, root: Path) -> bool:
        """应用 patch 文件"""
        import subprocess

        try:
            # 尝试使用 git apply
            result = subprocess.run(
                ["git", "apply", "--whitespace=nowarn", str(patch_file)],
                check=False,
                cwd=root,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return True

            # 回退到 patch 命令
            result = subprocess.run(
                ["patch", "-p1", "-i", str(patch_file)],
                check=False,
                cwd=root,
                capture_output=True,
                text=True,
            )
            return result.returncode == 0

        except FileNotFoundError:
            # git/patch 不可用，手动应用
            return self._manual_apply_patch(patch_file, root)

    def _manual_apply_patch(self, patch_file: Path, root: Path) -> bool:
        """手动应用 patch（当 git/patch 不可用时）"""
        patch_content = patch_file.read_text(encoding="utf-8")

        # 简单解析 unified diff
        current_file = None
        hunks: dict[Path, list[tuple[int, list[str], list[str]]]] = {}

        lines = patch_content.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i]

            # 文件头
            if line.startswith("--- a/"):
                i += 1
                if i < len(lines) and lines[i].startswith("+++ b/"):
                    current_file = root / lines[i][6:]
                    hunks[current_file] = []
                i += 1
                continue

            # Hunk 头
            if line.startswith("@@") and current_file:
                # 解析 @@ -start,count +start,count @@
                parts = line.split()
                if len(parts) >= 3:
                    old_info = parts[1]  # -start,count
                    old_start = int(old_info.split(",")[0][1:])

                    # 收集 hunk 内容
                    i += 1
                    old_lines = []
                    new_lines = []
                    while i < len(lines) and not lines[i].startswith(("@@", "---", "+++")):
                        hline = lines[i]
                        if hline.startswith("-"):
                            old_lines.append(hline[1:])
                        elif hline.startswith("+"):
                            new_lines.append(hline[1:])
                        elif hline.startswith(" "):
                            old_lines.append(hline[1:])
                            new_lines.append(hline[1:])
                        i += 1

                    hunks[current_file].append((old_start, old_lines, new_lines))
                    continue

            i += 1

        # 应用修改
        for file, file_hunks in hunks.items():
            if not file.exists():
                continue

            content = file.read_text(encoding="utf-8")
            file_lines = content.splitlines()

            # 从后往前应用 hunks
            for start, old_lines, new_lines in reversed(file_hunks):
                start_idx = start - 1
                end_idx = start_idx + len(old_lines)
                file_lines[start_idx:end_idx] = new_lines

            file.write_text("\n".join(file_lines) + "\n", encoding="utf-8")

        return True

    def undo(self, patch_file: Path, root: Path) -> bool:
        """撤销 patch"""
        import subprocess

        try:
            # 尝试使用 git apply -R
            result = subprocess.run(
                ["git", "apply", "-R", "--whitespace=nowarn", str(patch_file)],
                check=False,
                cwd=root,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                return True

            # 回退到 patch -R
            result = subprocess.run(
                ["patch", "-R", "-p1", "-i", str(patch_file)],
                check=False,
                cwd=root,
                capture_output=True,
                text=True,
            )
            return result.returncode == 0

        except FileNotFoundError:
            # 暂不支持手动撤销
            return False

    def list_patches(self, root: Path) -> list[Path]:
        """列出所有 patch 文件"""
        patch_dir = root / self.patch_dir
        if not patch_dir.exists():
            return []
        return sorted(patch_dir.glob("*.patch"), reverse=True)

    def get_latest_patch(self, root: Path) -> Path | None:
        """获取最新的 patch 文件"""
        patches = self.list_patches(root)
        return patches[0] if patches else None

    def preview_patch(self, patch_file: Path) -> str:
        """预览 patch 内容"""
        return patch_file.read_text(encoding="utf-8")
