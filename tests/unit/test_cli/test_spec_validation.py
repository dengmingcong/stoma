"""测试 make 命令的 spec 参数校验。"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from src.cli import app


class TestMakeSpecValidation:
    """测试 make 命令的 spec 参数校验。"""

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
        from tests.unit.test_cli.conftest import MALFORMED_YAML

        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(MALFORMED_YAML, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code != 0
