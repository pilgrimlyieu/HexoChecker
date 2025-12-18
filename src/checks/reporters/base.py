"""Reporter - 报告器抽象基类"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from checks.core.issue import Issue


class Reporter(ABC):
    """报告器抽象基类

    负责将检查结果以特定格式输出。
    """

    name: str = "base"
    description: str = "Base reporter"

    @abstractmethod
    def report(self, issues: list[Issue], root: Path) -> None:
        """输出检查结果

        Args:
            issues: 问题列表
            root: 项目根目录
        """
        ...

    @abstractmethod
    def report_issue(self, issue: Issue, root: Path) -> None:
        """输出单个问题

        Args:
            issue: 问题实例
            root: 项目根目录
        """
        ...

    def report_summary(self, issues: list[Issue]) -> None:  # noqa: B027
        """输出摘要信息

        Args:
            issues: 问题列表
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"
