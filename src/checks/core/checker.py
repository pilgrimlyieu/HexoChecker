"""Checker - 检查器抽象基类"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from checks.core.context import CheckContext
    from checks.core.issue import Fix, Issue


class Checker(ABC):
    """检查器抽象基类

    所有检查器都需要继承此类并实现 check 方法。

    Attributes:
        name: 检查器名称，用于标识和配置
        description: 检查器描述
        enabled: 是否启用
    """

    name: str = "base"
    description: str = "Base checker"
    enabled: bool = True

    @abstractmethod
    def check(self, file: Path, content: str, ctx: CheckContext) -> list[Issue]:
        """检查文件内容，返回问题列表

        Args:
            file: 被检查的文件路径
            content: 文件内容
            ctx: 检查上下文

        Returns:
            发现的问题列表
        """
        ...

    def can_fix(self, issue: Issue) -> bool:
        """判断是否能自动修复此问题

        Args:
            issue: 问题实例

        Returns:
            是否可修复
        """
        return issue.has_suggestion

    def get_fix(self, issue: Issue) -> Fix | None:
        """获取问题的修复方案

        Args:
            issue: 问题实例

        Returns:
            修复方案，无法修复时返回 None
        """
        return issue.get_fix()

    def supports_file(self, file: Path) -> bool:  # noqa: ARG002
        """判断检查器是否支持此文件类型

        子类可以覆盖此方法以限制检查的文件类型。

        Args:
            file: 文件路径

        Returns:
            是否支持
        """
        return True

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, enabled={self.enabled})"
