"""Reporters module - 输出报告器"""

from checks.reporters.base import Reporter
from checks.reporters.console import ConsoleReporter

__all__ = [
    "ConsoleReporter",
    "Reporter",
]
