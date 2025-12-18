"""
Hexo 博客检查器配置文件

此配置文件用于检查 Hexo 博客中的图片路径等问题。
放置于 %BLOG%/tools/checks/ 目录中。
"""

from pathlib import Path

from checks import Config, FixConfig, OutputConfig
from checks.checkers import ImageChecker
from checks.reporters import ConsoleReporter
from checks.reporters.console import ColorMode
from checks.resolvers import HexoResolver

# =============================================================================
# 检查器配置
# =============================================================================

# 图片检查器
image_checker = ImageChecker(
    # 忽略外部链接
    ignore_external=True,
    # 模糊匹配阈值（0-1）
    fuzzy_threshold=0.6,
    # 跳过代码块和行内代码
    skip_code_blocks=True,
    skip_inline_code=True,
    # 检查 HTML img 标签和 video poster
    check_html_img=True,
    check_video_poster=True,
)

# =============================================================================
# 路径解析器配置
# =============================================================================

# Hexo 路径解析器
hexo_resolver = HexoResolver(
    # 文章目录
    post_dir=["_posts", "_drafts"],
    # 启用文章资源文件夹（同名目录）
    asset_folder_per_post=True,
    # 普通页面目录
    pages=["daily", "domain", "notes"],
)

# =============================================================================
# 输出配置
# =============================================================================

# 终端报告器
console_reporter = ConsoleReporter(
    # 显示的上下文行数
    context_lines=3,
    # 显示修复建议
    show_suggestions=True,
    # 颜色模式: auto, always, never
    color=ColorMode.AUTO,
    # 显示行号
    line_numbers=True,
    # 使用 Unicode 框线字符
    box_drawing=True,
)

# =============================================================================
# 主配置
# =============================================================================

config = Config(
    # 项目根目录（相对于配置文件）
    # 配置文件在 tools/checks/，source 在 ../source
    root=Path(__file__).parent.parent.parent / "source",
    # 要检查的文件模式
    include=[
        "_posts/**/*.md",
        "_drafts/**/*.md",
        "daily/**/*.md",
        "domain/**/*.md",
        "notes/**/*.md",
    ],
    # 排除的文件模式
    exclude=[
        "**/node_modules/**",
        "**/.git/**",
    ],
    # 路径解析器
    resolver=hexo_resolver,
    # 检查器列表
    checkers=[
        image_checker,
    ],
    # 报告器
    reporter=console_reporter,
    # 输出配置
    output=OutputConfig(
        context_lines=3,
        show_suggestions=True,
        color="auto",
    ),
    # 修复配置
    fix=FixConfig(
        patch_dir=".checks/patches",
        auto_backup=True,
        dry_run=False,
    ),
)


# =============================================================================
# 钩子函数（可选）
# =============================================================================


def before_check(ctx):
    """检查开始前的钩子"""
    pass


def after_check(ctx, issues):
    """检查完成后的钩子"""
    pass


# 注册钩子
config.before_check = before_check
config.after_check = after_check
