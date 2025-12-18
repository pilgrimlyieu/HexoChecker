"""InteractiveFixer - 交互式修复器"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from checks.fixers.base import FixAction, Fixer, FixResult, FixSession
from checks.fixers.patch import PatchFixer
from checks.reporters.console import ConsoleReporter

if TYPE_CHECKING:
    from pathlib import Path

    from checks.core.context import CheckContext
    from checks.core.issue import Issue


@dataclass
class InteractiveFixer(Fixer):
    """交互式修复器

    逐个展示问题并询问用户是否修复。

    Attributes:
        reporter: 用于显示问题的 reporter
        patch_fixer: 用于生成 patch 的 fixer
    """

    name: str = "interactive"
    description: str = "Interactive fixer with user confirmation"

    reporter: ConsoleReporter = field(default_factory=ConsoleReporter)
    patch_fixer: PatchFixer = field(default_factory=PatchFixer)

    # 帮助信息
    _help_text: str = """
    \033[95my\033[0m - Accept this fix
    \033[95mn\033[0m - Skip this issue
    \033[95ma\033[0m - Accept all remaining fixes
    \033[95mq\033[0m - Quit (generate patch for accepted fixes)
    \033[95md\033[0m - Show detailed diff preview
    \033[95m?\033[0m - Show this help
    """

    def fix(self, issues: list[Issue], root: Path, dry_run: bool = False) -> FixSession:
        """交互式修复"""
        session = FixSession()

        # 过滤可修复的问题
        fixable = self.filter_fixable(issues)
        if not fixable:
            print("\033[92m✓ No fixable issues found\033[0m")
            session.complete()
            return session

        print(f"\nFound \033[93m{len(fixable)}\033[0m fixable issue(s)")
        print("─" * 40)

        # 收集要修复的问题
        to_fix: list[Issue] = []
        accept_all = False

        for i, issue in enumerate(fixable, 1):
            if accept_all:
                to_fix.append(issue)
                session.results.append(
                    FixResult(issue=issue, action=FixAction.ACCEPT, fix=issue.get_fix())
                )
                continue

            # 显示问题
            print(f"\n[{i}/{len(fixable)}]")
            self.reporter.report_issue(issue, root)

            # 获取用户选择
            action = self._prompt_action(issue, root)

            match action:
                case FixAction.ACCEPT:
                    to_fix.append(issue)
                    session.results.append(
                        FixResult(issue=issue, action=FixAction.ACCEPT, fix=issue.get_fix())
                    )
                    print("\033[92m✓ Accepted\033[0m")

                case FixAction.SKIP:
                    session.results.append(FixResult(issue=issue, action=FixAction.SKIP))
                    print("\033[93m○ Skipped\033[0m")

                case FixAction.ACCEPT_ALL:
                    accept_all = True
                    to_fix.append(issue)
                    session.results.append(
                        FixResult(issue=issue, action=FixAction.ACCEPT, fix=issue.get_fix())
                    )
                    print("\033[92m✓ Accepting all remaining fixes...\033[0m")

                case FixAction.QUIT:
                    print("\033[93m⚠ Quit requested\033[0m")
                    break

        # 应用修复
        if to_fix:
            print()
            print("─" * 40)
            print(f"Applying \033[92m{len(to_fix)}\033[0m fix(es)...")

            if dry_run:
                print("\033[93m[DRY RUN] No changes made\033[0m")
            else:
                # 使用 PatchFixer 生成和应用 patch
                self.patch_fixer.fix(to_fix, root, dry_run=False)

                # 更新 applied 状态
                for result in session.results:
                    if result.action == FixAction.ACCEPT:
                        result.applied = True

                # 显示 patch 文件位置
                latest_patch = self.patch_fixer.get_latest_patch(root)
                if latest_patch:
                    try:
                        rel_patch = latest_patch.relative_to(root)
                    except ValueError:
                        rel_patch = latest_patch
                    print(f"\033[90mPatch saved to: {rel_patch}\033[0m")

        # 显示摘要
        self._print_summary(session)

        session.complete()
        return session

    def _prompt_action(self, issue: Issue, root: Path) -> FixAction:
        """提示用户选择操作"""
        while True:
            try:
                prompt = "\033[95m[y]es [n]o [a]ll [q]uit [d]iff [?]help\033[0m: "
                choice = input(prompt).strip().lower()

                match choice:
                    case "y" | "yes":
                        return FixAction.ACCEPT
                    case "n" | "no":
                        return FixAction.SKIP
                    case "a" | "all":
                        return FixAction.ACCEPT_ALL
                    case "q" | "quit":
                        return FixAction.QUIT
                    case "d" | "diff":
                        self._show_diff_preview(issue, root)
                    case "?" | "help":
                        print(self._help_text)
                    case "":
                        # 默认跳过
                        return FixAction.SKIP
                    case _:
                        print(f"\033[91mUnknown option: {choice}\033[0m")

            except EOFError:
                return FixAction.QUIT
            except KeyboardInterrupt:
                print()
                return FixAction.QUIT

    def _show_diff_preview(self, issue: Issue, root: Path) -> None:  # noqa: ARG002
        """显示 diff 预览"""
        fix = issue.get_fix()
        if not fix:
            print("\033[91mNo fix available\033[0m")
            return

        print()
        print("\033[90m--- Original\033[0m")
        print(f"\033[91m- {fix.original}\033[0m")
        print("\033[90m+++ Fixed\033[0m")
        print(f"\033[92m+ {fix.replacement}\033[0m")
        print()

    def _print_summary(self, session: FixSession) -> None:
        """打印修复摘要"""
        accepted = len([r for r in session.results if r.action == FixAction.ACCEPT])
        skipped = len([r for r in session.results if r.action == FixAction.SKIP])
        applied = len([r for r in session.results if r.applied])

        print()
        print("═" * 40)
        print("Summary:")
        if applied:
            print(f"  \033[92m✓ {applied} fix(es) applied\033[0m")
        if accepted - applied:
            print(f"  \033[93m○ {accepted - applied} fix(es) pending\033[0m")
        if skipped:
            print(f"  \033[90m○ {skipped} issue(s) skipped\033[0m")
        print("═" * 40)


def run_interactive_fix(
    issues: list[Issue], root: Path, ctx: CheckContext | None = None, dry_run: bool = False
) -> FixSession:
    """便捷函数：运行交互式修复"""
    fixer = InteractiveFixer()

    # 填充上下文信息
    if ctx:
        for issue in issues:
            if issue.context is None:
                issue.context = ctx.get_context_lines(
                    issue.file,
                    issue.line,
                    before=fixer.reporter.context_lines,
                    after=fixer.reporter.context_lines,
                )

    return fixer.fix(issues, root, dry_run=dry_run)
