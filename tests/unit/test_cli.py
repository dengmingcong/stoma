"""CLI 命令的单元测试。

测试 stoma make 命令的：
- 成功路径：从有效 OpenAPI 生成代码文件
- 错误路径：参数校验失败、OpenAPI 解析失败、版本不支持
- 文件命名：基于 operationId
- 输出：每个 endpoint 生成独立 .py 文件
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from src.cli import app

runner = CliRunner()


VALID_OPENAPI_YAML = """\
openapi: 3.1.0
info:
  title: Test API
  version: "1.0.0"
paths:
  /users:
    get:
      operationId: listUsers
      summary: 列出用户
      responses:
        "200":
          description: 成功
  /users/{user_id}:
    get:
      operationId: getUser
      summary: 获取用户
      parameters:
        - name: user_id
          in: path
          required: true
          schema:
            type: string
      responses:
        "200":
          description: 成功
    delete:
      operationId: deleteUser
      summary: 删除用户
      parameters:
        - name: user_id
          in: path
          required: true
          schema:
            type: string
      responses:
        "204":
          description: 成功
"""

INVALID_OPENAPI_YAML = """\
openapi: 2.0.0
info:
  title: Old API
  version: "1.0.0"
paths: {}
"""

MALFORMED_YAML = """\
openapi: 3.0.0
info: not a valid info
"""

EMPTY_OPENAPI_YAML = """\
openapi: 3.0.0
info:
  title: Empty API
  version: "1.0.0"
paths: {}
"""


class TestMakeSuccess:
    """测试 make 命令的成功路径。"""

    def test_generates_files_for_each_endpoint(self, tmp_path: Path) -> None:
        """验证每个 endpoint 生成独立文件。"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(VALID_OPENAPI_YAML, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        assert (out_dir / "listUsers.py").exists()
        assert (out_dir / "getUser.py").exists()
        assert (out_dir / "deleteUser.py").exists()

    def test_generates_valid_python_syntax(self, tmp_path: Path) -> None:
        """验证生成的代码是有效的 Python 语法。"""
        import ast

        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(VALID_OPENAPI_YAML, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        for generated in out_dir.glob("*.py"):
            ast.parse(generated.read_text(encoding="utf-8"))

    def test_creates_output_dir_if_missing(self, tmp_path: Path) -> None:
        """验证输出目录不存在时自动创建。"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(VALID_OPENAPI_YAML, encoding="utf-8")
        out_dir = tmp_path / "deep" / "nested" / "output"

        result = runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        assert out_dir.exists()
        assert out_dir.is_dir()

    def test_empty_paths_generates_no_files(self, tmp_path: Path) -> None:
        """验证没有 endpoint 的 OpenAPI 不会报错。"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(EMPTY_OPENAPI_YAML, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        assert list(out_dir.glob("*.py")) == []

    def test_output_message_lists_generated_files(self, tmp_path: Path) -> None:
        """验证输出信息包含生成的文件名。"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(VALID_OPENAPI_YAML, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        assert "listUsers.py" in result.output
        assert "getUser.py" in result.output
        assert "deleteUser.py" in result.output


class TestMakeSpecValidation:
    """测试 make 命令的 spec 参数校验。"""

    def test_missing_spec_file(self, tmp_path: Path) -> None:
        """验证 spec 文件不存在时报错。"""
        spec_file = tmp_path / "missing.yaml"
        out_dir = tmp_path / "output"

        result = runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code != 0
        assert "文件不存在" in result.output

    def test_spec_is_directory(self, tmp_path: Path) -> None:
        """验证 spec 是目录时报错。"""
        out_dir = tmp_path / "output"

        result = runner.invoke(app, [str(tmp_path), "--out", str(out_dir)])

        assert result.exit_code != 0
        assert "不是文件" in result.output

    def test_malformed_yaml(self, tmp_path: Path) -> None:
        """验证 spec 文件格式错误时报错。"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(MALFORMED_YAML, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code != 0


class TestMakeOpenAPIValidation:
    """测试 OpenAPI 规范的校验。"""

    def test_unsupported_version(self, tmp_path: Path) -> None:
        """验证不支持的 OpenAPI 版本报错。"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(INVALID_OPENAPI_YAML, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code != 0
        assert "Unsupported OpenAPI version" in result.output

    def test_json_spec_accepted(self, tmp_path: Path) -> None:
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

        result = runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        assert (out_dir / "ping.py").exists()


class TestMakeFileNaming:
    """测试生成文件的命名规则。"""

    def test_filename_uses_operation_id(self, tmp_path: Path) -> None:
        """验证文件名基于 operationId（snake_case 等价）。"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(VALID_OPENAPI_YAML, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        # listUsers、getUser、deleteUser 是 camelCase，文件名保持原样。
        assert (out_dir / "listUsers.py").exists()
        assert (out_dir / "getUser.py").exists()
        assert (out_dir / "deleteUser.py").exists()

    def test_snake_case_operation_id(self, tmp_path: Path) -> None:
        """验证 snake_case 的 operationId 直接用作文件名。"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(
            """\
openapi: 3.1.0
info:
  title: Snake API
  version: "1.0.0"
paths:
  /items:
    get:
      operationId: list_items
      summary: 列出
      responses:
        "200":
          description: ok
""",
            encoding="utf-8",
        )
        out_dir = tmp_path / "output"

        result = runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        assert (out_dir / "list_items.py").exists()


class TestMakeOptions:
    """测试 make 命令的选项。"""

    def test_short_option_flag(self, tmp_path: Path) -> None:
        """验证 -o 短选项也能正常工作。"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(EMPTY_OPENAPI_YAML, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = runner.invoke(app, [str(spec_file), "-o", str(out_dir)])

        assert result.exit_code == 0, result.output
        assert out_dir.exists()

    def test_help_message(self) -> None:
        """验证 help 命令正常工作。"""
        result = runner.invoke(app, ["--help"])

        assert result.exit_code == 0
        assert "OpenAPI" in result.output
        assert "--out" in result.output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
