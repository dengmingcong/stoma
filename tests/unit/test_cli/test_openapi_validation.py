"""测试 OpenAPI 规范的校验。"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from src.cli import app
from src.openapi.parser import make_openapi_parser


class TestMakeOpenAPIValidation:
    """测试 OpenAPI 规范的校验。"""

    def test_unsupported_version(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """验证不支持的 OpenAPI 版本报错。"""
        from tests.unit.test_cli.conftest import INVALID_OPENAPI_YAML

        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(INVALID_OPENAPI_YAML, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code != 0
        assert "Unsupported OpenAPI version" in result.output

    def test_json_spec_accepted(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """验证 JSON 格式的 OpenAPI 规范也能处理。"""
        spec_file = tmp_path / "spec.json"
        spec_file.write_text(
            """{
  "openapi": "3.1.0",
  "info": {"title": "JSON API", "version": "1.0.0"},
  "paths": {
    "/ping": {
      "get": {
        "operationId": "ping",
        "summary": "ping",
        "responses": {"200": {"description": "ok"}}
      }
    }
  }
}""",
            encoding="utf-8",
        )
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        assert (out_dir / "ping.py").exists()

    def test_parser_loads_v30_spec(self, valid_v30_spec: Path) -> None:
        """验证 ``make_openapi_parser`` 能识别 OpenAPI 3.0.x 规范。

        工厂按 ``openapi`` 版本字符串前缀注入 3.0 模型类，断言：
        1. ``load()`` 不抛异常
        2. ``spec_version == "3.0"``
        3. 解析出 2 个 endpoint（``getUser`` / ``createUser``）
        """
        parser = make_openapi_parser(valid_v30_spec)
        parser.load()
        assert parser.spec_version == "3.0"
        endpoints = parser.get_endpoints()
        assert len(endpoints) == 2
        assert {endpoint.operation_id for endpoint in endpoints} == {"getUser", "createUser"}
