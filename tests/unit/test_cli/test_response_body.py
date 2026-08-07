"""测试各种 response body 场景的生成结果。"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from src.cli import app


class TestMakeResponseBody:
    """测试各种 response body 场景的生成结果。"""

    def test_response_with_ref_schema(self, cli_runner: CliRunner, tmp_path: Path) -> None:
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

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "get_user.py").read_text(encoding="utf-8")
        # response 类型为 User，从 .models 导入。
        assert "APIRoute[User]" in content
        assert "from .models import User" in content

    def test_response_with_array_of_ref(self, cli_runner: CliRunner, tmp_path: Path) -> None:
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

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "list_users.py").read_text(encoding="utf-8")
        # datamodel-codegen 包装 array-of-ref response 时按 operationId 派生
        #（``listUsers`` → ``ListUsersResponse``），renderer 同步引用同名，
        # 由 ``use_operation_id_as_name=True`` 触发。
        assert "APIRoute[ListUsersResponse]" in content
        assert "from .models import ListUsersResponse" in content

    def test_response_with_nested_object_schema(self, cli_runner: CliRunner, tmp_path: Path) -> None:
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

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        assert (out_dir / "get_profile.py").exists()
        content = (out_dir / "get_profile.py").read_text(encoding="utf-8")
        assert "@router.get" in content
        # 嵌套对象响应也按 operationId 派生模型名（``getProfile`` → ``GetProfileResponse``），
        # 从 .models 导入，由 ``use_operation_id_as_name=True`` 触发。
        assert "from .models import GetProfileResponse" in content
        assert "APIRoute[GetProfileResponse]" in content

    def test_response_201_uses_201_status(self, cli_runner: CliRunner, tmp_path: Path) -> None:
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

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "create_user.py").read_text(encoding="utf-8")
        assert "APIRoute[User]" in content

    def test_response_without_content(self, cli_runner: CliRunner, tmp_path: Path) -> None:
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

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "delete_item.py").read_text(encoding="utf-8")
        # 无 content-type 为 json 的响应，不生成泛型参数。
        assert "APIRoute)" in content

    def test_response_with_non_snake_case_fields(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """验证 response 顶层字段非 snake_case 时自动追加 ``alias=<origin>``。

        回归测试：response 由 ``datamodel-code-generator`` 生成的 model
        承担 schema 校验职责，字段命名同样受 ``snake_case_field=True``
        影响——非 snake_case 字段必须带 ``alias=<origin>``，否则反序列化
        API 实际 payload 时会丢失字段。

        覆盖：
        - camelCase ``widgetId`` / ``widgetName`` → snake + alias
        - PascalCase ``CreatedAt`` → snake + alias
        - 已 snake_case ``item_count`` → 不加 alias
        """
        spec = """\
openapi: 3.1.0
info:
  title: Mixed Naming Response API
  version: "1.0.0"
paths:
  /widgets:
    get:
      operationId: listWidgets
      summary: 列出 widgets（response 含非蛇形字段）
      responses:
        "200":
          description: ok
          content:
            application/json:
              schema:
                type: object
                required: [widgetId, widgetName]
                properties:
                  widgetId:
                    type: string
                  widgetName:
                    type: string
                  item_count:
                    type: integer
                  CreatedAt:
                    type: string
                    format: date-time
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        models = (out_dir / "models.py").read_text(encoding="utf-8")

        # camelCase → snake + alias 保留原名。
        assert 'widget_id: str = Field(..., alias="widgetId")' in models
        assert 'widget_name: str = Field(..., alias="widgetName")' in models
        # PascalCase → snake + alias 保留原名。
        assert 'created_at: AwareDatetime | None = Field(None, alias="CreatedAt")' in models
        # 已 snake_case → 保持裸声明，不冗余加 alias。
        assert "item_count: int | None = None" in models
        assert 'item_count: int | None = Field(None, alias="item_count")' not in models

    def test_response_with_nested_non_snake_case_fields(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """验证 response 嵌套对象内的非 snake_case 字段同样自动添加 ``alias``。

        回归测试：``datamodel-code-generator`` 对每一层嵌套对象独立应用
        ``snake_case_field`` 转换，所有非 snake_case 字段（包括嵌套层）都
        必须携带 ``alias=<origin>``，否则反序列化 API 实际 payload 时会
        丢失嵌套层字段。
        """
        spec = """\
openapi: 3.1.0
info:
  title: Nested Non-Snake Response API
  version: "1.0.0"
paths:
  /orders:
    get:
      operationId: getOrder
      summary: 获取订单（嵌套 response 含非蛇形字段）
      responses:
        "200":
          description: ok
          content:
            application/json:
              schema:
                type: object
                required: [orderInfo]
                properties:
                  orderInfo:
                    type: object
                    required: [orderId]
                    properties:
                      orderId:
                        type: string
                      shippingAddress:
                        type: object
                        properties:
                          streetName:
                            type: string
                          ZIPCode:
                            type: string
                  totalAmount:
                    type: number
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        models = (out_dir / "models.py").read_text(encoding="utf-8")

        # 顶层非 snake_case 字段加 alias。
        assert 'order_info: OrderInfo = Field(..., alias="orderInfo")' in models
        assert 'total_amount: float | None = Field(None, alias="totalAmount")' in models
        # 嵌套对象独立生成 model，字段同样满足 alias 约定。
        assert 'order_id: str = Field(..., alias="orderId")' in models
        # 嵌套内的嵌套（含全大写字段名）也命中 alias。
        assert 'street_name: str | None = Field(None, alias="streetName")' in models
        assert 'zip_code: str | None = Field(None, alias="ZIPCode")' in models
