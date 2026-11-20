"""单元测试共享的 fixtures 和 OpenAPI 规范常量。

从 :mod:`tests.unit.test_cli.conftest`（已删除）迁移而来，集中暴露：

- ``cli_runner``：Typer ``CliRunner`` 实例，所有需要调用 ``src.cli:app`` 的测试都用它。
- ``valid_spec``：写入 ``VALID_OPENAPI_YAML`` 并返回 ``(spec_file, out_dir)`` 元组，
  CLI 端到端用例复用。
- ``valid_v30_spec``：OpenAPI 3.0.x 规范，仅 ``src.openapi.parser`` 涉及 3.0 解析路径
  的测试需要。
- ``assert_field_line`` / ``assert_models_import``：与排版无关的断言助手。

关于两个断言助手（2026-11-20）
--------------------------------

CLI 生成代码后**不做格式化** —— 排版由使用者自行处理（见 ``docs/guide/cli.md``）。
因此生成的代码里：

- 字符串字面量用单引号（``Field(serialization_alias='X')``），
- ``from ..models import ...`` 按 spec 顺序列出，而非字母序。

这两种差异都是**排版**，不是**语义**。断言若写死双引号或字母序，就把排版
当成了行为契约 —— 框架行为没变，测试却会红。

于是提供两个助手，断言**语义**而非排版：

- ``assert_field_line(content, "authorization", "Annotated[str, Header(), Field(...)]")``
  —— 引号风格不敏感；字段名与类型/元数据必须精确匹配。
- ``assert_models_import(route, "Error", "User")`` —— 模型**集合**必须匹配（顺序不敏感），
  且不多不少。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

runner = CliRunner()


VALID_OPENAPI_YAML: str = """\
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

INVALID_OPENAPI_YAML: str = """\
openapi: 2.0.0
info:
  title: Old API
  version: "1.0.0"
paths: {}
"""

MALFORMED_YAML: str = """\
openapi: 3.0.0
info: not a valid info
"""

EMPTY_OPENAPI_YAML: str = """\
openapi: 3.1.0
info:
  title: Empty API
  version: "1.0.0"
paths: {}
"""

OPENAPI_30_SPEC: str = """\
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


def _normalize_quotes(text: str) -> str:
    """把 Python 字符串字面量的引号统一成双引号，便于跨引号风格比较。

    只处理成对的 ``'...'`` / ``"..."``，不触碰转义引号内的内容。
    """
    return re.sub(r"'([^'\"\\]*)'", r'"\1"', text)


def assert_field_line(content: str, field_name: str, annotation: str) -> None:
    """断言生成的代码里有 ``field_name: annotation`` 这一行。

    引号风格不敏感 —— ``annotation`` 里的单引号与双引号视为等价。
    字段名与类型/元数据必须精确匹配。

    :param content: 生成的 Python 源码。
    :param field_name: 字段名（snake_case）。
    :param annotation: 期望的类型注解，如
        ``Annotated[str, Header(), Field(serialization_alias='Authorization')]``。
    """
    normalized = _normalize_quotes(content)
    expected = _normalize_quotes(f"{field_name}: {annotation}")
    assert expected in normalized, f"期望包含 {expected!r}\n实际内容:\n{content}"


def assert_models_import(route: str, *models: str) -> None:
    """断言生成的 route 里 ``from ..models import ...`` 导入了恰好这些模型。

    顺序不敏感 —— 生成器按 spec 顺序列出，格式化工具（ruff isort）会按
    字母序重排，两者都合法。模型**集合**必须匹配：不多、不少、不少导入。

    注意：本助手只校验**导入的模型集合**，不校验顺序 —— 顺序由 spec 决定，
    属渲染细节。

    :param route: 生成的 route 源码。
    :param models: 期望导入的模型名。
    """
    match = re.search(r"^from \.\.models import (.+)$", route, flags=re.MULTILINE)
    assert match is not None, f"route 里没有 `from ..models import ...`\n实际内容:\n{route}"
    imported = {name.strip() for name in match.group(1).split(",")}
    expected = set(models)
    assert imported == expected, f"期望导入 {sorted(expected)}，实际 {sorted(imported)}\n实际内容:\n{route}"


__all__ = [
    "EMPTY_OPENAPI_YAML",
    "INVALID_OPENAPI_YAML",
    "MALFORMED_YAML",
    "OPENAPI_30_SPEC",
    "VALID_OPENAPI_YAML",
    "assert_field_line",
    "assert_models_import",
    "cli_runner",
    "valid_spec",
    "valid_v30_spec",
]
