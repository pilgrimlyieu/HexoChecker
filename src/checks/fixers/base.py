"""Fixer - 修复器抽象基类"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from checks.core.issue import Fix, Issue


class FixAction(Enum):
    """修复动作"""

    ACCEPT = "accept"  # 接受修复
    SKIP = "skip"  # 跳过
    ACCEPT_ALL = "accept_all"  # 接受所有
    QUIT = "quit"  # 退出


@dataclass
class FixResult:
    """修复结果"""

    issue: Issue
    action: FixAction
    fix: Fix | None = None
    applied: bool = False
    error: str | None = None

    @property
    def was_fixed(self) -> bool:
        """是否成功修复"""
        return self.applied and self.action == FixAction.ACCEPT


@dataclass
class FixSession:
    """修复会话

    记录一次修复操作的所有信息，用于生成 patch 和撤销。
    """

    id: str = field(default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S"))
    results: list[FixResult] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None

    @property
    def accepted_fixes(self) -> list[FixResult]:
        """获取已接受的修复"""
        return [r for r in self.results if r.was_fixed]

    @property
    def skipped_count(self) -> int:
        """跳过的数量"""
        return sum(1 for r in self.results if r.action == FixAction.SKIP)

    def complete(self):
        """标记会话完成"""
        self.completed_at = datetime.now()


class Fixer(ABC):
    """修复器抽象基类

    负责应用修复方案到文件。
    """

    name: str = "base"
    description: str = "Base fixer"

    @abstractmethod
    def fix(self, issues: list[Issue], root: Path, dry_run: bool = False) -> FixSession:
        """执行修复

        Args:
            issues: 可修复的问题列表
            root: 项目根目录
            dry_run: 是否只预览不实际修改

        Returns:
            修复会话
        """
        ...

    def can_fix(self, issue: Issue) -> bool:
        """判断是否能修复此问题"""
        return issue.has_suggestion

    def filter_fixable(self, issues: list[Issue]) -> list[Issue]:
        """过滤出可修复的问题"""
        return [i for i in issues if self.can_fix(i)]

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"
