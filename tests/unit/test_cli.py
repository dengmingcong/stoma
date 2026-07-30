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
        assert (out_dir / "list_users.py").exists()
        assert (out_dir / "get_user.py").exists()
        assert (out_dir / "delete_user.py").exists()

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
        """验证输出信息包含生成的文件名（snake_case）。"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(VALID_OPENAPI_YAML, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        assert "list_users.py" in result.output
        assert "get_user.py" in result.output
        assert "delete_user.py" in result.output


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

    def test_camelcase_operation_id_becomes_snake_case(self, tmp_path: Path) -> None:
        """验证 camelCase 的 operationId 转为 snake_case 文件名。"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(VALID_OPENAPI_YAML, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        # listUsers → list_users.py
        assert (out_dir / "list_users.py").exists()
        assert (out_dir / "get_user.py").exists()
        assert (out_dir / "delete_user.py").exists()

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

    def test_pascalcase_operation_id_becomes_snake_case(self, tmp_path: Path) -> None:
        """验证 PascalCase 的 operationId 转为 snake_case 文件名。"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(
            """\
openapi: 3.1.0
info:
  title: Pascal API
  version: "1.0.0"
paths:
  /items:
    get:
      operationId: ListItems
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

    def test_class_name_in_file_is_pascal_case(self, tmp_path: Path) -> None:
        """验证文件名是 snake_case 但类名是 PascalCase。"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(
            """\
openapi: 3.1.0
info:
  title: Class API
  version: "1.0.0"
paths:
  /users:
    get:
      operationId: listUsers
      summary: 列出用户
      responses:
        "200":
          description: ok
""",
            encoding="utf-8",
        )
        out_dir = tmp_path / "output"

        result = runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        # 文件名是 snake_case。
        assert (out_dir / "list_users.py").exists()
        # 类名是 PascalCase。
        content = (out_dir / "list_users.py").read_text(encoding="utf-8")
        assert "class ListUsers" in content


class TestMakeRequestBody:
    """测试各种 requestBody 场景的生成结果。"""

    @staticmethod
    def _build_spec(path: str, method: str, operation_id: str, request_body_block: str) -> str:
        """构造一个包含 requestBody 的 OpenAPI 3.1 规范。"""
        return f"""\
openapi: 3.1.0
info:
  title: Body API
  version: "1.0.0"
paths:
  {path}:
    {method}:
      operationId: {operation_id}
      summary: 测试
      requestBody:
{request_body_block}
      responses:
        "200":
          description: ok
"""

    def test_request_body_with_ref_schema(self, tmp_path: Path) -> None:
        """验证 requestBody 使用 $ref 引用的 schema 时能正常生成。"""
        spec = self._build_spec(
            "/users",
            "post",
            "createUser",
            """\
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/User'
components:
  schemas:
    User:
      type: object
      required: [id, name]
      properties:
        id:
          type: string
        name:
          type: string
""",
        )
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        assert (out_dir / "create_user.py").exists()
        content = (out_dir / "create_user.py").read_text(encoding="utf-8")
        # 生成的代码应该包含 User 模型（作为内嵌 BaseModel）。
        assert "class User" in content
        assert "BaseModel" in content

    def test_request_body_with_inline_object_schema(self, tmp_path: Path) -> None:
        """验证 requestBody 使用内联 object schema 时能正常生成。"""
        spec = self._build_spec(
            "/items",
            "post",
            "createItem",
            """\
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [name]
              properties:
                name:
                  type: string
                quantity:
                  type: integer
""",
        )
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        assert (out_dir / "create_item.py").exists()
        content = (out_dir / "create_item.py").read_text(encoding="utf-8")
        assert "@router.post" in content

    def test_request_body_with_nested_object_schema(self, tmp_path: Path) -> None:
        """验证 requestBody 使用嵌套 object schema 时能正常生成。"""
        spec = self._build_spec(
            "/orders",
            "post",
            "createOrder",
            """\
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [customer, items]
              properties:
                customer:
                  type: object
                  required: [id]
                  properties:
                    id:
                      type: string
                    name:
                      type: string
                items:
                  type: array
                  items:
                    type: object
                    required: [sku]
                    properties:
                      sku:
                        type: string
                      quantity:
                        type: integer
""",
        )
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "create_order.py").read_text(encoding="utf-8")
        # 嵌套对象可以正常生成。
        assert "createOrder" in content or "create_order" in content
        assert "@router.post" in content

    def test_request_body_with_array_schema(self, tmp_path: Path) -> None:
        """验证 requestBody 为数组类型时能正常生成。"""
        spec = self._build_spec(
            "/batch",
            "post",
            "createBatch",
            """\
        required: true
        content:
          application/json:
            schema:
              type: array
              items:
                $ref: '#/components/schemas/Item'
components:
  schemas:
    Item:
      type: object
      required: [id]
      properties:
        id:
          type: string
""",
        )
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        assert (out_dir / "create_batch.py").exists()

    def test_request_body_with_no_body(self, tmp_path: Path) -> None:
        """验证 endpoint 没有 requestBody 时不报错。"""
        spec = """\
openapi: 3.1.0
info:
  title: No Body API
  version: "1.0.0"
paths:
  /health:
    get:
      operationId: health
      summary: 健康检查
      responses:
        "200":
          description: ok
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "health.py").read_text(encoding="utf-8")
        assert "@router.get" in content


class TestMakeResponseBody:
    """测试各种 response body 场景的生成结果。"""

    def test_response_with_ref_schema(self, tmp_path: Path) -> None:
        """验证 response 使用 $ref 引用的 schema 时生成对应模型。"""
        spec = """\
openapi: 3.1.0
info:
  title: Response API
  version: "1.0.0"
paths:
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
          description: ok
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/User'
        "404":
          description: 用户不存在
components:
  schemas:
    User:
      type: object
      required: [id, name]
      properties:
        id:
          type: string
        name:
          type: string
        email:
          type: string
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "get_user.py").read_text(encoding="utf-8")
        # response 类型为 User，类生成包含 User 模型定义。
        assert "APIRoute[User]" in content
        assert "class User" in content

    def test_response_with_array_of_ref(self, tmp_path: Path) -> None:
        """验证 response 为引用类型的数组时生成 list[Model]。"""
        spec = """\
openapi: 3.1.0
info:
  title: List API
  version: "1.0.0"
paths:
  /users:
    get:
      operationId: listUsers
      summary: 列出用户
      responses:
        "200":
          description: ok
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/User'
components:
  schemas:
    User:
      type: object
      required: [id]
      properties:
        id:
          type: string
        name:
          type: string
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "list_users.py").read_text(encoding="utf-8")
        assert "APIRoute[list[User]]" in content
        assert "class User" in content

    def test_response_with_nested_object_schema(self, tmp_path: Path) -> None:
        """验证 response 为嵌套对象时能正常生成。"""
        spec = """\
openapi: 3.1.0
info:
  title: Nested API
  version: "1.0.0"
paths:
  /profile:
    get:
      operationId: getProfile
      summary: 获取个人资料
      responses:
        "200":
          description: ok
          content:
            application/json:
              schema:
                type: object
                required: [user, settings]
                properties:
                  user:
                    type: object
                    required: [id]
                    properties:
                      id:
                        type: string
                      avatar:
                        type: string
                  settings:
                    type: object
                    properties:
                      theme:
                        type: string
                      notifications:
                        type: boolean
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        assert (out_dir / "get_profile.py").exists()
        content = (out_dir / "get_profile.py").read_text(encoding="utf-8")
        assert "@router.get" in content

    def test_response_201_uses_201_status(self, tmp_path: Path) -> None:
        """验证 201 Created 响应也能正确识别。"""
        spec = """\
openapi: 3.1.0
info:
  title: Created API
  version: "1.0.0"
paths:
  /users:
    post:
      operationId: createUser
      summary: 创建用户
      responses:
        "201":
          description: 创建成功
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/User'
components:
  schemas:
    User:
      type: object
      required: [id]
      properties:
        id:
          type: string
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "create_user.py").read_text(encoding="utf-8")
        assert "APIRoute[User]" in content

    def test_response_without_content(self, tmp_path: Path) -> None:
        """验证 response 只有 description 没有 content 时生成 None 类型。"""
        spec = """\
openapi: 3.1.0
info:
  title: No Content API
  version: "1.0.0"
paths:
  /items/{item_id}:
    delete:
      operationId: deleteItem
      summary: 删除
      parameters:
        - name: item_id
          in: path
          required: true
          schema:
            type: string
      responses:
        "204":
          description: 删除成功
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "delete_item.py").read_text(encoding="utf-8")
        # 响应类型默认为 None。
        assert "APIRoute[None]" in content


class TestMakeParameters:
    """测试各种 parameter 场景的生成结果。"""

    def test_query_parameters_with_types(self, tmp_path: Path) -> None:
        """验证不同类型的 query 参数被正确映射为 Python 类型。"""
        spec = """\
openapi: 3.1.0
info:
  title: Params API
  version: "1.0.0"
paths:
  /search:
    get:
      operationId: search
      summary: 搜索
      parameters:
        - name: q
          in: query
          required: true
          schema:
            type: string
        - name: limit
          in: query
          required: false
          schema:
            type: integer
        - name: score
          in: query
          required: false
          schema:
            type: number
        - name: active
          in: query
          required: false
          schema:
            type: boolean
      responses:
        "200":
          description: ok
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "search.py").read_text(encoding="utf-8")
        # Python 类型映射正确。
        assert "q: str" in content
        assert "limit: int = None" in content
        assert "score: float = None" in content
        assert "active: bool = None" in content

    def test_header_parameter_uses_annotated(self, tmp_path: Path) -> None:
        """验证 header 参数使用 Annotated[..., Header(...)] 标记。"""
        spec = """\
openapi: 3.1.0
info:
  title: Header API
  version: "1.0.0"
paths:
  /auth:
    get:
      operationId: checkAuth
      summary: 检查权限
      parameters:
        - name: Authorization
          in: header
          required: true
          schema:
            type: string
        - name: X-Request-ID
          in: header
          required: false
          schema:
            type: string
      responses:
        "200":
          description: ok
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "check_auth.py").read_text(encoding="utf-8")
        # header 参数走 header_params，不出现在 param_fields 中。
        assert "from stoma import router, APIRoute, Header" in content
        assert "from typing import Annotated" in content
        assert "Authorization" not in content or "Annotated" in content

    def test_required_vs_optional_path_param(self, tmp_path: Path) -> None:
        """验证 path 参数必填、无默认值。"""
        spec = """\
openapi: 3.1.0
info:
  title: Path API
  version: "1.0.0"
paths:
  /items/{item_id}:
    get:
      operationId: getItem
      summary: 获取
      parameters:
        - name: item_id
          in: path
          required: true
          schema:
            type: string
      responses:
        "200":
          description: ok
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "get_item.py").read_text(encoding="utf-8")
        assert "item_id: str" in content
        # required 参数不应有 = None 默认值。
        assert "item_id: str = None" not in content


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
