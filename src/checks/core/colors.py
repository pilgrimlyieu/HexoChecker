"""ANSI 颜色代码管理

统一管理终端输出的颜色代码，避免硬编码散落各处。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Color(Enum):
    """ANSI 颜色代码"""

    # 前景色
    BLACK = "30"
    RED = "31"
    GREEN = "32"
    YELLOW = "33"
    BLUE = "34"
    MAGENTA = "35"
    CYAN = "36"
    WHITE = "37"

    # 亮色
    BRIGHT_BLACK = "90"
    BRIGHT_RED = "91"
    BRIGHT_GREEN = "92"
    BRIGHT_YELLOW = "93"
    BRIGHT_BLUE = "94"
    BRIGHT_MAGENTA = "95"
    BRIGHT_CYAN = "96"
    BRIGHT_WHITE = "97"

    # 重置
    RESET = "0"


@dataclass(frozen=True)
class Style:
    """预定义样式"""

    # 状态
    SUCCESS: str = f"\033[{Color.BRIGHT_GREEN.value}m"
    ERROR: str = f"\033[{Color.BRIGHT_RED.value}m"
    WARNING: str = f"\033[{Color.BRIGHT_YELLOW.value}m"
    INFO: str = f"\033[{Color.BRIGHT_CYAN.value}m"
    MUTED: str = f"\033[{Color.BRIGHT_BLACK.value}m"

    # 内容
    ORIGINAL: str = f"\033[{Color.BRIGHT_RED.value}m"
    SUGGESTION: str = f"\033[{Color.BRIGHT_GREEN.value}m"
    HIGHLIGHT: str = f"\033[{Color.BRIGHT_MAGENTA.value}m"

    # 重置
    RESET: str = "\033[0m"


# 全局样式实例
style = Style()


def colorize(text: str, color: Color | str) -> str:
    """为文本添加颜色

    Args:
        text: 要着色的文本
        color: 颜色代码或 Color 枚举

    Returns:
        带 ANSI 颜色代码的字符串
    """
    code = color.value if isinstance(color, Color) else color
    return f"\033[{code}m{text}\033[0m"


def success(text: str) -> str:
    """成功样式（绿色）"""
    return f"{style.SUCCESS}{text}{style.RESET}"


def error(text: str) -> str:
    """错误样式（红色）"""
    return f"{style.ERROR}{text}{style.RESET}"


def warning(text: str) -> str:
    """警告样式（黄色）"""
    return f"{style.WARNING}{text}{style.RESET}"


def info(text: str) -> str:
    """信息样式（青色）"""
    return f"{style.INFO}{text}{style.RESET}"


def muted(text: str) -> str:
    """淡化样式（灰色）"""
    return f"{style.MUTED}{text}{style.RESET}"
