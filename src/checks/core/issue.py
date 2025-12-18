"""Issue - 问题模型定义"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class Severity(Enum):
    """问题严重程度"""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

    def __str__(self) -> str:
        return self.value


@dataclass
class ContextLines:
    """上下文行信息"""

    before: list[tuple[int, str]]  # [(行号, 内容), ...]
    current: tuple[int, str]  # (行号, 内容)
    after: list[tuple[int, str]]  # [(行号, 内容), ...]

    @property
    def all_lines(self) -> list[tuple[int, str]]:
        """获取所有行（包括上下文）"""
        return [*self.before, self.current, *self.after]


@dataclass
class Fix:
    """修复方案"""

    original: str  # 原始文本
    replacement: str  # 替换文本
    line: int  # 所在行号
    start_col: int | None = None  # 起始列（None 表示整行替换）
    end_col: int | None = None  # 结束列
    description: str = ""  # 修复描述

    def apply_to_line(self, line_content: str) -> str:
        """将修复应用到行内容"""
        if self.start_col is None:
            # 基于文本匹配替换
            return line_content.replace(self.original, self.replacement, 1)
        else:
            # 精确位置替换
            end = self.end_col if self.end_col is not None else self.start_col + len(self.original)
            return line_content[: self.start_col] + self.replacement + line_content[end:]


@dataclass
class Issue:
    """表示检查发现的一个问题"""

    file: Path  # 问题所在文件
    line: int  # 行号（1-based）
    type: str  # 问题类型标识
    message: str  # 问题描述
    original: str  # 原始内容（整行或片段）
    checker: str  # 来源检查器名称

    # 可选字段
    column: int | None = None  # 列号（可选）
    suggestion: str | None = None  # 建议修复文本
    severity: Severity = Severity.ERROR  # 严重程度
    metadata: dict[str, Any] = field(default_factory=dict)  # 额外元数据

    # 运行时填充
    context: ContextLines | None = None  # 上下文行信息

    def __post_init__(self):
        """确保 file 是 Path 对象"""
        if isinstance(self.file, str):
            self.file = Path(self.file)

    @property
    def has_suggestion(self) -> bool:
        """是否有修复建议"""
        return self.suggestion is not None

    @property
    def location(self) -> str:
        """格式化的位置字符串"""
        if self.column is not None:
            return f"{self.file}:{self.line}:{self.column}"
        return f"{self.file}:{self.line}"

    def get_fix(self) -> Fix | None:
        """获取修复方案"""
        if self.suggestion is None:
            return None
        return Fix(
            original=self.original,
            replacement=self.suggestion,
            line=self.line,
            start_col=self.column,
            description=f"Fix {self.type}: {self.message}",
        )

    def __str__(self) -> str:
        return f"[{self.severity}] {self.location}: {self.message}"

    def __repr__(self) -> str:
        return (
            f"Issue(file={self.file!r}, line={self.line}, "
            f"type={self.type!r}, message={self.message!r})"
        )
