"""CLI - 命令行接口"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from checks import __version__

if TYPE_CHECKING:
    from checks.config import Config


def main(argv: list[str] | None = None) -> int:
    """主入口函数"""
    parser = create_parser()
    args = parser.parse_args(argv)

    # 根据子命令执行
    if hasattr(args, "func"):
        return args.func(args)
    else:
        parser.print_help()
        return 0


def _load_config_or_exit(config_path: Path | None) -> tuple[Config, Path]:
    """加载配置文件，失败时打印错误并退出

    Args:
        config_path: 配置文件路径（可选）

    Returns:
        (配置对象, 配置目录)

    Raises:
        SystemExit: 加载失败时
    """
    from checks.config import load_config
    from checks.core.colors import error

    try:
        return load_config(config_path)
    except (FileNotFoundError, ImportError) as e:
        print(error(f"Error loading config: {e}"), file=sys.stderr)
        sys.exit(1)


def create_parser() -> argparse.ArgumentParser:
    """创建命令行解析器"""
    parser = argparse.ArgumentParser(
        prog="checks",
        description="Extensible content checker for blogs and documentation",
    )
    parser.add_argument("--version", "-V", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--config", "-c", type=Path, help="Path to config file (checks_config.py)")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # check 命令
    check_parser = subparsers.add_parser("check", help="Run checks on files")
    check_parser.add_argument(
        "--include", "-I", action="append", default=[], help="Additional glob patterns to include"
    )
    check_parser.add_argument(
        "--exclude", "-E", action="append", default=[], help="Additional glob patterns to exclude"
    )
    check_parser.add_argument(
        "--checker", action="append", default=[], help="Only run specified checker(s)"
    )
    check_parser.add_argument("--json", action="store_true", help="Output in JSON format")
    check_parser.add_argument("--quiet", "-q", action="store_true", help="Only show summary")
    check_parser.set_defaults(func=cmd_check)

    # fix 命令
    fix_parser = subparsers.add_parser("fix", help="Fix detected issues")
    fix_parser.add_argument(
        "--interactive", "-i", action="store_true", default=True, help="Interactive mode (default)"
    )
    fix_parser.add_argument(
        "--all", "-a", action="store_true", help="Accept all fixes without prompting"
    )
    fix_parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes without applying"
    )
    fix_parser.set_defaults(func=cmd_fix)

    # undo 命令
    undo_parser = subparsers.add_parser("undo", help="Undo a patch")
    undo_parser.add_argument(
        "patch", nargs="?", type=Path, help="Patch file to undo (default: latest)"
    )
    undo_parser.add_argument(
        "--list", "-l", action="store_true", dest="list_patches", help="List all patches"
    )
    undo_parser.set_defaults(func=cmd_undo)

    # list 命令
    list_parser = subparsers.add_parser("list", help="List available components")
    list_parser.add_argument("--checkers", action="store_true", help="List available checkers")
    list_parser.add_argument("--resolvers", action="store_true", help="List available resolvers")
    list_parser.set_defaults(func=cmd_list)

    return parser


def cmd_check(args: argparse.Namespace) -> int:
    """执行 check 命令"""
    from checks.runner import CheckRunner

    # 加载配置
    config, config_dir = _load_config_or_exit(args.config)

    # 合并命令行参数
    if args.include:
        config.include.extend(args.include)
    if args.exclude:
        config.exclude.extend(args.exclude)
    if args.checker:
        config.checkers = [c for c in config.checkers if c.name in args.checker]

    # 运行检查
    root = config.resolve_root(config_dir)
    runner = CheckRunner(config=config, root=root)

    if args.json:
        issues = runner.run(report=False)
        _output_json(issues, root)
    elif args.quiet:
        issues = runner.run(report=False)
        _output_summary(issues)
    else:
        issues = runner.run(report=True)

    # 返回码：有错误返回 1
    from checks.core.issue import Severity

    has_errors = any(i.severity == Severity.ERROR for i in issues)
    return 1 if has_errors else 0


def cmd_fix(args: argparse.Namespace) -> int:
    """执行 fix 命令"""
    from checks.core.colors import success
    from checks.fixers.interactive import InteractiveFixer
    from checks.fixers.patch import PatchFixer
    from checks.runner import CheckRunner

    # 加载配置
    config, config_dir = _load_config_or_exit(args.config)

    # 运行检查（不输出）
    root = config.resolve_root(config_dir)
    runner = CheckRunner(config=config, root=root)
    issues = runner.run(report=False)

    # 过滤可修复的问题
    fixable = [i for i in issues if i.has_suggestion]
    if not fixable:
        print(success("✓ No fixable issues found"))
        return 0

    # 选择修复器
    if args.all:
        fixer = PatchFixer(patch_dir=Path(config.fix.patch_dir))
        fixer.fix(fixable, root, dry_run=args.dry_run)
    else:
        fixer = InteractiveFixer()
        fixer.patch_fixer.patch_dir = Path(config.fix.patch_dir)
        fixer.fix(fixable, root, dry_run=args.dry_run)

    return 0


def cmd_undo(args: argparse.Namespace) -> int:
    """执行 undo 命令"""
    from checks.core.colors import error, success
    from checks.fixers.patch import PatchFixer

    # 加载配置
    config, config_dir = _load_config_or_exit(args.config)

    root = config.resolve_root(config_dir)
    fixer = PatchFixer(patch_dir=Path(config.fix.patch_dir))

    # 列出 patches
    if args.list_patches:
        patches = fixer.list_patches(root)
        if not patches:
            print("No patches found")
            return 0

        print("Available patches:")
        for patch in patches:
            try:
                rel = patch.relative_to(root)
            except ValueError:
                rel = patch
            print(f"  {rel}")
        return 0

    # 撤销 patch
    if args.patch:
        patch_file = Path(args.patch)
        if not patch_file.is_absolute():
            patch_file = root / patch_file
    else:
        patch_file = fixer.get_latest_patch(root)
        if not patch_file:
            print(error("No patches to undo"))
            return 1

    if not patch_file.exists():
        print(error(f"Patch file not found: {patch_file}"))
        return 1

    print(f"Undoing patch: {patch_file.name}")
    if fixer.undo(patch_file, root):
        print(success("✓ Patch reverted successfully"))

        # 询问是否删除 patch 文件
        try:
            choice = input("Delete patch file? [y/N]: ").strip().lower()
            if choice in ("y", "yes"):
                patch_file.unlink()
                print("Patch file deleted")
        except (EOFError, KeyboardInterrupt):
            pass

        return 0
    else:
        print(error("✗ Failed to revert patch"))
        return 1


def cmd_list(args: argparse.Namespace) -> int:
    """执行 list 命令"""
    from checks.checkers import ImageChecker
    from checks.core.colors import info
    from checks.resolvers import DefaultResolver, HexoResolver

    if args.checkers or (not args.checkers and not args.resolvers):
        print("Available checkers:")
        print(f"  {info('image')} - {ImageChecker.description}")

    if args.resolvers or (not args.checkers and not args.resolvers):
        print("\nAvailable resolvers:")
        print(f"  {info('default')} - {DefaultResolver.description}")
        print(f"  {info('hexo')} - {HexoResolver.description}")

    return 0

    return 0


def _output_json(issues: list, root: Path) -> None:
    """输出 JSON 格式"""
    import json

    output = []
    for issue in issues:
        try:
            rel_path = issue.file.relative_to(root)
        except ValueError:
            rel_path = issue.file

        output.append(
            {
                "file": rel_path.as_posix(),
                "line": issue.line,
                "column": issue.column,
                "type": issue.type,
                "message": issue.message,
                "severity": str(issue.severity),
                "suggestion": issue.suggestion,
                "checker": issue.checker,
            }
        )

    print(json.dumps(output, indent=2, ensure_ascii=False))


def _output_summary(issues: list) -> None:
    """输出摘要"""
    from checks.core.issue import Severity

    if not issues:
        print("\033[92m✓ No issues found\033[0m")
        return

    errors = sum(1 for i in issues if i.severity == Severity.ERROR)
    warnings = sum(1 for i in issues if i.severity == Severity.WARNING)
    fixable = sum(1 for i in issues if i.has_suggestion)

    parts = []
    if errors:
        parts.append(f"\033[91m{errors} error(s)\033[0m")
    if warnings:
        parts.append(f"\033[93m{warnings} warning(s)\033[0m")

    print(f"Found {', '.join(parts)}")
    if fixable:
        print(f"\033[92m  {fixable} can be auto-fixed\033[0m")


if __name__ == "__main__":
    sys.exit(main())
