"""测试 make 命令的选项。"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from src.cli import app


class TestMakeOptions:
    """测试 make 命令的选项。"""

    def test_short_option_flag(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """验证 -o 短选项也能正常工作。"""
        from tests.unit.test_cli.conftest import EMPTY_OPENAPI_YAML

        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(EMPTY_OPENAPI_YAML, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "-o", str(out_dir)])

        assert result.exit_code == 0, result.output
        assert out_dir.exists()

    def test_help_message(self, cli_runner: CliRunner) -> None:
        """验证 help 命令正常工作。"""
        result = cli_runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "OpenAPI" in result.output
        assert "--out" in result.output
