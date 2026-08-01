"""测试 make 命令的成功路径。"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from src.cli import app


class TestMakeSuccess:
    """测试 make 命令的成功路径。"""

    def test_generates_files_for_each_endpoint(
        self, cli_runner: CliRunner, tmp_path: Path, valid_spec: tuple[Path, Path]
    ) -> None:
        """验证每个 endpoint 生成独立文件。"""
        spec_file, out_dir = valid_spec

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        assert (out_dir / "list_users.py").exists()
        assert (out_dir / "get_user.py").exists()
        assert (out_dir / "delete_user.py").exists()

    def test_generates_valid_python_syntax(
        self, cli_runner: CliRunner, tmp_path: Path, valid_spec: tuple[Path, Path]
    ) -> None:
        """验证生成的代码是有效的 Python 语法。"""
        import ast

        spec_file, out_dir = valid_spec

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        for generated in out_dir.glob("*.py"):
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
        from tests.unit.test_cli.conftest import EMPTY_OPENAPI_YAML

        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(EMPTY_OPENAPI_YAML, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        assert list(out_dir.glob("*.py")) == []

    def test_output_message_lists_generated_files(self, cli_runner: CliRunner, valid_spec: tuple[Path, Path]) -> None:
        """验证输出信息包含生成的文件名（snake_case）。"""
        spec_file, out_dir = valid_spec

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        assert "list_users.py" in result.output
        assert "get_user.py" in result.output
        assert "delete_user.py" in result.output
