# Checks - 可扩展的博客内容检查框架

一个可扩展的博客/文档内容检查框架，支持图片路径验证、链接检查等多种检查类型，提供插件化架构、Python 配置、交互式修复和友好的终端输出。

## 特性

- 🔌 **插件化架构** - 检查器、路径解析器、报告器均可自定义扩展
- 🐍 **Python 配置** - 使用 Python 文件配置，支持复杂逻辑
- 🎨 **友好输出** - 类似 delta/git diff 风格的彩色终端输出
- 🔧 **安全修复** - 基于 Patch 文件的修复机制，支持撤销
- 🎯 **Hexo 支持** - 内置 Hexo 博客的特殊路径处理

## 安装

```bash
# 使用 uv
uv sync

# 或直接运行
checks
```

## 快速开始

### 1. 创建配置文件

在项目根目录创建 `checks_config.py`：

```python
from checks import Config
from checks.checkers import ImageChecker
from checks.resolvers import HexoResolver

config = Config(
    root=".",
    include=["**/*.md"],
    exclude=["**/node_modules/**"],
    resolver=HexoResolver(
        post_dir=["_posts"],
        asset_folder_per_post=True,
    ),
    checkers=[
        ImageChecker(
            ignore_external=True,
            fuzzy_threshold=0.6,
        ),
    ],
)
```

### 2. 运行检查

```bash
# 检查所有文件
checks check

# 或使用 Python 模块
python -m checks check
```

### 3. 修复问题

```bash
# 交互式修复
checks fix

# 自动接受所有修复
checks fix --all

# 预览修改（不实际应用）
checks fix --dry-run
```

### 4. 撤销修复

```bash
# 撤销最近的修复
checks undo

# 列出所有 patch 文件
checks undo --list

# 撤销指定 patch
checks undo .checks/patches/2024-01-15_143052.patch
```

## 命令行接口

```
checks [OPTIONS] COMMAND

Commands:
  check    运行检查
  fix      修复问题
  undo     撤销修复
  list     列出可用组件

Options:
  --config, -c PATH    指定配置文件
  --version, -V        显示版本
  --help, -h           显示帮助
```

### check 命令

```
checks check [OPTIONS]

Options:
  --include, -I PATTERN  额外包含的文件模式
  --exclude, -E PATTERN  额外排除的文件模式
  --checker NAME         只运行指定检查器
  --json                 输出 JSON 格式
  --quiet, -q            只显示摘要
```

### fix 命令

```
checks fix [OPTIONS]

Options:
  --interactive, -i  交互式修复（默认）
  --all, -a          自动接受所有修复
  --dry-run          预览修改，不实际应用
```

## 配置详解

### 完整配置示例

```python
from checks import Config, OutputConfig, FixConfig
from checks.checkers import ImageChecker
from checks.resolvers import HexoResolver
from checks.reporters import ConsoleReporter

config = Config(
    # 项目根目录
    root="..",
    
    # 要检查的文件
    include=[
        "_posts/**/*.md",
        "pages/**/*.md",
    ],
    
    # 排除的文件
    exclude=[
        "**/_drafts/**",
        "**/node_modules/**",
    ],
    
    # 路径解析器
    resolver=HexoResolver(
        post_dir=["_posts"],
        asset_folder_per_post=True,
    ),
    
    # 检查器
    checkers=[
        ImageChecker(
            ignore_external=True,
            fuzzy_threshold=0.6,
            skip_code_blocks=True,
            skip_inline_code=True,
            check_html_img=True,
            check_video_poster=True,
        ),
    ],
    
    # 报告器
    reporter=ConsoleReporter(
        context_lines=3,
        show_suggestions=True,
        color="auto",
    ),
    
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
    ),
)
```

### 钩子函数

```python
def before_check(ctx):
    """检查开始前"""
    print(f"Checking in {ctx.root}")

def after_check(ctx, issues):
    """检查完成后"""
    print(f"Found {len(issues)} issues")

config.before_check = before_check
config.after_check = after_check
```

## 扩展指南

### 自定义检查器

```python
from pathlib import Path

from checks.core.checker import Checker
from checks.core.context import CheckContext
from checks.core.issue import Issue, Severity

class CustomChecker(Checker):
    name = "custom"
    description = "My custom checker"
    
    def check(self, file: Path, content: str, ctx: CheckContext) -> list[Issue]:
        issues = []
        # 实现检查逻辑
        return issues
```

### 自定义路径解析器

```python
from pathlib import Path

from checks.core.context import CheckContext
from checks.core.resolver import PathResolver

class CustomResolver(PathResolver):
    name = "custom"
    description = "My custom resolver"
    
    def resolve(self, path: str, source_file: Path, ctx: CheckContext) -> Path | None:
        # 实现路径解析逻辑
        pass
    
    def exists(self, path: str, source_file: Path, ctx: CheckContext) -> bool:
        resolved = self.resolve(path, source_file, ctx)
        return resolved is not None and resolved.exists()
```

## 输出示例

```
╭─ _posts/2024-01-01-hello.md
│
│  40 │ Some text before the image
│  41 │ Here is some context line
│  42 │ ![screenshot](images/screnshot.png)
│     │               ^^^^^^^^^^^^^^^^^^^^
│     │ ✗ Image not found: `images/screnshot.png`
│     │ → Did you mean: `images/screenshot.png`
│  43 │ More text after the image
│  44 │ Another context line
│
╰──

Found 1 error(s)
  1 issue(s) can be auto-fixed
```

## 项目结构

```
src/checks/
├── __init__.py           # 包入口
├── core/                 # 核心组件
│   ├── issue.py          # Issue 数据类
│   ├── checker.py        # Checker 基类
│   ├── resolver.py       # PathResolver 基类
│   └── context.py        # CheckContext
├── checkers/             # 检查器实现
│   └── image.py          # 图片检查器
├── resolvers/            # 路径解析器
│   ├── default.py        # 默认解析器
│   └── hexo.py           # Hexo 解析器
├── reporters/            # 报告器
│   ├── base.py           # 基类
│   └── console.py        # 终端输出
├── fixers/               # 修复器
│   ├── base.py           # 基类
│   ├── patch.py          # Patch 修复器
│   └── interactive.py    # 交互式修复器
├── config.py             # 配置系统
├── runner.py             # 检查运行器
└── cli.py                # 命令行接口
```

## License

MIT
