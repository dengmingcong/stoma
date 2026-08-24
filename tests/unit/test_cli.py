"""``src.cli:app`` 的 Typer 命令单元测试。

合并自 :mod:`tests.unit.test_cli` 包内的 ``test_options`` / ``test_spec_validation``
/ ``test_success``：

- :class:`TestMakeOptions` —— ``-o`` 短选项、``--help``。
- :class:`TestMakeSpecValidation` —— spec 文件不存在、是目录、YAML 格式错误。
- :class:`TestMakeSuccess` —— 每个 endpoint 生成文件、生成代码是有效 Python 语法、
  自动创建输出目录、空 paths 不报错、输出消息列出生成文件。

共享的 OpenAPI YAML 字符串与 ``cli_runner`` / ``valid_spec`` fixtures 定义在
:mod:`tests.unit.conftest`。
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

from typer.testing import CliRunner

from stoma.cli import app
from tests.unit.conftest import EMPTY_OPENAPI_YAML, MALFORMED_YAML


class TestMakeOptions:
    """``make`` 命令的选项。"""

    def test_short_option_flag(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """验证 ``-o`` 短选项也能正常工作。"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(EMPTY_OPENAPI_YAML, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "-o", str(out_dir)])

        assert result.exit_code == 0, result.output
        assert out_dir.exists()

    def test_help_message(self, cli_runner: CliRunner) -> None:
        """验证 ``--help`` 命令正常工作。"""
        result = cli_runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        # 去除 ANSI 颜色代码后检查。
        clean = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
        assert "OpenAPI" in clean
        assert "--out" in clean


class TestMakeSpecValidation:
    """``make`` 命令的 spec 参数校验。"""

    def test_missing_spec_file(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """验证 spec 文件不存在时报错。"""
        spec_file = tmp_path / "missing.yaml"
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code != 0
        assert "文件不存在" in result.output

    def test_spec_is_directory(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """验证 spec 是目录时报错。"""
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(tmp_path), "--out", str(out_dir)])

        assert result.exit_code != 0
        assert "不是文件" in result.output

    def test_malformed_yaml(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """验证 spec 文件格式错误时报错。"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(MALFORMED_YAML, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code != 0


class TestMakeSuccess:
    """``make`` 命令的成功路径。"""

    def test_generates_files_for_each_endpoint(self, cli_runner: CliRunner, valid_spec: tuple[Path, Path]) -> None:
        """验证每个 endpoint 生成独立文件。"""
        spec_file, out_dir = valid_spec

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        assert (out_dir / "endpoints" / "list_users.py").exists()
        assert (out_dir / "endpoints" / "get_user.py").exists()
        assert (out_dir / "endpoints" / "delete_user.py").exists()

    def test_generates_valid_python_syntax(self, cli_runner: CliRunner, valid_spec: tuple[Path, Path]) -> None:
        """验证生成的代码是有效的 Python 语法。"""
        spec_file, out_dir = valid_spec

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        for generated in (out_dir / "endpoints").glob("*.py"):
            ast.parse(generated.read_text(encoding="utf-8"))

    def test_creates_output_dir_if_missing(
        self, cli_runner: CliRunner, tmp_path: Path, valid_spec: tuple[Path, Path]
    ) -> None:
        """验证输出目录不存在时自动创建。"""
        spec_file, _ = valid_spec
        out_dir = tmp_path / "deep" / "nested" / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        assert out_dir.exists()
        assert out_dir.is_dir()

    def test_empty_paths_generates_no_files(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """验证没有 endpoint 的 OpenAPI 不会报错。"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(EMPTY_OPENAPI_YAML, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        endpoint_files = [f for f in (out_dir / "endpoints").glob("*.py") if f.name != "__init__.py"]
        assert endpoint_files == []

