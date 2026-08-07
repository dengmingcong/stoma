"""CLI 测试共享的 fixtures 和 OpenAPI 规范。"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

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
openapi: 3.1.0
info:
  title: Empty API
  version: "1.0.0"
paths: {}
"""


@pytest.fixture
def cli_runner() -> CliRunner:
    """提供 CLI 测试运行器。"""
    return runner


@pytest.fixture
def valid_spec(tmp_path: Path) -> tuple[Path, Path]:
    """创建有效的 OpenAPI spec 文件和输出目录。"""
    spec_file = tmp_path / "spec.yaml"
    spec_file.write_text(VALID_OPENAPI_YAML, encoding="utf-8")
    out_dir = tmp_path / "output"
    return spec_file, out_dir
