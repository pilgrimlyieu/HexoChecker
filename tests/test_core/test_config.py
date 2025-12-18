"""Tests for Config"""

from pathlib import Path

import pytest

from checks.config import Config, load_config


class TestConfig:
    """Config 测试"""

    def test_default_config(self) -> None:
        """测试默认配置"""
        config = Config()

        assert config.root == Path()
        assert config.resolver is not None  # 默认创建 DefaultResolver
        assert isinstance(config.checkers, list)  # 默认检查器
        assert "**/*.md" in config.include
        assert config.output.context_lines == 3

    def test_config_with_excludes(self) -> None:
        """测试排除模式"""
        config = Config(
            root=".",
            exclude=["node_modules/**", "*.bak"],
        )

        assert "node_modules/**" in config.exclude
        assert "*.bak" in config.exclude

    def test_config_root_as_path(self) -> None:
        """测试 Path 类型的 root"""
        config = Config(root=Path("/some/path"))

        assert isinstance(config.root, Path)
        assert config.root == Path("/some/path")

    def test_config_custom_pattern(self) -> None:
        """测试自定义文件模式"""
        config = Config(
            root=".",
            include=["**/*.markdown"],
        )

        assert "**/*.markdown" in config.include


class TestLoadConfig:
    """load_config 测试"""

    def test_load_valid_config(self, tmp_path: Path) -> None:
        """测试加载有效配置文件"""
        config_file = tmp_path / "checks_config.py"
        config_file.write_text(
            """
from pathlib import Path
from checks.config import Config

config = Config(
    root=Path("."),
    include=["**/*.md"],
)
""",
            encoding="utf-8",
        )

        config, config_dir = load_config(config_file)

        assert isinstance(config, Config)
        assert "**/*.md" in config.include
        assert config_dir == tmp_path

    def test_load_nonexistent_file(self, tmp_path: Path) -> None:
        """测试加载不存在的文件"""
        with pytest.raises(FileNotFoundError):
            load_config(tmp_path / "nonexistent.py")

    def test_load_invalid_python(self, tmp_path: Path) -> None:
        """测试加载语法错误的 Python 文件"""
        config_file = tmp_path / "checks_config.py"
        config_file.write_text("def invalid syntax", encoding="utf-8")

        with pytest.raises(ImportError):
            load_config(config_file)

    def test_load_missing_config_variable(self, tmp_path: Path) -> None:
        """测试加载缺少 config 变量的文件"""
        config_file = tmp_path / "checks_config.py"
        config_file.write_text("x = 1", encoding="utf-8")

        with pytest.raises(ImportError) as exc_info:
            load_config(config_file)

        assert "config" in str(exc_info.value).lower()

    def test_load_wrong_type_config(self, tmp_path: Path) -> None:
        """测试 config 变量类型错误"""
        config_file = tmp_path / "checks_config.py"
        config_file.write_text("config = 'not a config'", encoding="utf-8")

        with pytest.raises(ImportError) as exc_info:
            load_config(config_file)

        assert "Config" in str(exc_info.value)
