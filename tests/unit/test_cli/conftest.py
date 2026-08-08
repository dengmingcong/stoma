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

OPENAPI_30_SPEC = """\
openapi: 3.0.3
info:
  title: Test API
  version: "1.0.0"
paths:
  /users/{user_id}:
    get:
      operationId: getUser
      summary: 获取用户
      parameters:
        - $ref: '#/components/parameters/UserIdParam'
      responses:
        "200":
          description: OK
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/User'
  /users:
    post:
      operationId: createUser
      summary: 创建用户
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/User'
      responses:
        "201":
          description: Created
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/User'
components:
  parameters:
    UserIdParam:
      name: user_id
      in: path
      required: true
      schema:
        type: string
  requestBodies:
    UserBody:
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/User'
  responses:
    UserResponse:
      description: OK
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/User'
  schemas:
    User:
      type: object
      properties:
        id:
          type: string
        name:
          type: string
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


@pytest.fixture
def valid_v30_spec(tmp_path: Path) -> Path:
    """创建 OpenAPI 3.0.x spec 文件并返回路径。

    用于验证 3.0 ``$ref`` 解析（parameter / requestBody / response）。
    """
    spec_file = tmp_path / "spec_v30.yaml"
    spec_file.write_text(OPENAPI_30_SPEC, encoding="utf-8")
    return spec_file
