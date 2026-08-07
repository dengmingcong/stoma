"""测试各种 requestBody 场景的生成结果。"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from src.cli import app


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


class TestMakeRequestBody:
    """测试各种 requestBody 场景的生成结果。"""

    def test_request_body_with_ref_schema(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """验证 requestBody 使用 $ref 引用的 schema 时能正常生成。"""
        spec = _build_spec(
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

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        assert (out_dir / "create_user.py").exists()
        content = (out_dir / "create_user.py").read_text(encoding="utf-8")
        # 生成的代码应该从 .models 导入 User（不再内联模型）。
        assert "from .models import User" in content
        # $ref 指向的 schema 有 title，render 为 case 1：body: <title>
        assert "body: User" in content

    def test_request_body_with_inline_object_schema(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """验证 requestBody 使用内联 object schema 时能正常生成。"""
        spec = _build_spec(
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

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        assert (out_dir / "create_item.py").exists()
        content = (out_dir / "create_item.py").read_text(encoding="utf-8")
        assert "@router.post" in content
        # 内联对象生成 CreateItemRequest 模型（operationId 派生，
        # ``createItem`` → ``CreateItemRequest``），由 ``use_operation_id_as_name=True`` 触发。
        assert "from .models import CreateItemRequest" in content
        assert "body: CreateItemRequest" in content

    def test_request_body_with_nested_object_schema(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """验证 requestBody 使用嵌套 object schema 时能正常生成。"""
        spec = _build_spec(
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

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "create_order.py").read_text(encoding="utf-8")
        # 嵌套对象可以正常生成。
        assert "createOrder" in content or "create_order" in content
        assert "@router.post" in content

    def test_request_body_with_array_schema(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """验证 requestBody 为数组类型时能正常生成。"""
        spec = _build_spec(
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

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        assert (out_dir / "create_batch.py").exists()

    def test_request_body_with_no_body(self, cli_runner: CliRunner, tmp_path: Path) -> None:
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

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "health.py").read_text(encoding="utf-8")
        assert "@router.get" in content

    def test_request_body_with_embed_true(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """验证 requestBody 使用 embed=True（单属性 wrapper）时生成 Body(embed=True)。"""
        spec = _build_spec(
            "/users",
            "post",
            "createUserEmbed",
            """\
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [data]
              properties:
                data:
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

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        assert (out_dir / "create_user_embed.py").exists()
        content = (out_dir / "create_user_embed.py").read_text(encoding="utf-8")
        # 按 operationId 派生（``createUserEmbed`` → ``CreateUserEmbedRequest``），
        # 由 ``use_operation_id_as_name=True`` 触发。
        # body 形态由 spec 决定。
        assert "body: CreateUserEmbedRequest" in content
        assert "from .models import CreateUserEmbedRequest" in content
        assert "from stoma import APIRouter, APIRoute, Body" in content

    def test_request_body_with_non_pascalcase_ref(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """验证 ``$ref`` 末段（``components.schemas`` 的 key）非 PascalCase 时被 PascalCase 化。

        回归测试：renderer 必须 PascalCase 化 ref 末段，与
        ``datamodel-code-generator`` 对 ``components.schemas`` key 的自动
        PascalCase 行为对齐。例如 ``components.schemas.user-profile`` 在
        dmcg 生成 ``class UserProfile``，renderer 也必须引用 ``UserProfile``
        而不是 ``user-profile``。
        """
        spec = """\
openapi: 3.1.0
info:
  title: Non-PascalCase Ref API
  version: "1.0.0"
paths:
  /profile:
    post:
      operationId: createProfile
      summary: 创建个人资料
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/user-profile'
      responses:
        "200":
          description: ok
components:
  schemas:
    user-profile:
      type: object
      required: [display_name]
      properties:
        display_name:
          type: string
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        assert (out_dir / "create_profile.py").exists()
        content = (out_dir / "create_profile.py").read_text(encoding="utf-8")
        # ref 末段 ``user-profile`` 必须 PascalCase 为 ``UserProfile``，与
        # ``datamodel-code-generator`` 对 ``components.schemas`` key 的处理对齐。
        assert "from .models import UserProfile" in content
        assert "body: UserProfile" in content

    def test_request_body_without_operation_id_errors(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """operationId 必填校验——缺 operationId 时 CLI 应清晰报错而不是 fallback 到 method+path。

        回归测试：``parser.validate_operation_ids()`` 检查到缺失 operationId 时
        抛出 ``OpenAPISchemaError``，cli.py 的 typer 错误处理器将其转换为
        ``typer.BadParameter`` 并输出友好错误信息。
        """
        spec = """\
openapi: 3.1.0
info:
  title: No OperationId API
  version: "1.0.0"
paths:
  /users:
    post:
      summary: 创建用户
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [name]
              properties:
                name:
                  type: string
      responses:
        "200":
          description: ok
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code != 0, result.output
        assert "operationId is required" in result.output

    def test_request_body_with_non_snake_case_fields(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """验证 requestBody 顶层字段非 snake_case 时自动追加 ``alias=<origin>``。

        回归测试：``datamodel-code-generator`` 在 ``snake_case_field=True`` 下
        对转换前后不一致的字段自动生成 ``Field(..., alias="<original>")``。
        已是 snake_case 的字段必须保持裸声明（不冗余加 alias）。

        覆盖：
        - camelCase ``firstName`` / ``isActive`` → snake + alias
        - PascalCase ``LastName`` / ``EmailAddress`` → snake + alias
        - 已 snake_case ``user_id`` → 不加 alias
        """
        spec = """\
openapi: 3.1.0
info:
  title: Mixed Naming API
  version: "1.0.0"
paths:
  /profiles:
    post:
      operationId: createProfile
      summary: 创建 profile（混合大小写命名）
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [firstName, LastName]
              properties:
                firstName:
                  type: string
                LastName:
                  type: string
                user_id:
                  type: string
                EmailAddress:
                  type: string
                  format: email
                isActive:
                  type: boolean
      responses:
        "200":
          description: ok
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        models = (out_dir / "models.py").read_text(encoding="utf-8")

        # camelCase → snake + alias 保留原名。
        assert 'first_name: str = Field(..., alias="firstName")' in models
        assert 'is_active: bool | None = Field(None, alias="isActive")' in models
        # PascalCase → snake + alias 保留原名。
        assert 'last_name: str = Field(..., alias="LastName")' in models
        assert 'email_address: EmailStr | None = Field(None, alias="EmailAddress")' in models
        # 已 snake_case → 保持裸声明，不冗余加 alias。
        assert "user_id: str | None = None" in models
        assert 'user_id: str | None = Field(None, alias="user_id")' not in models

    def test_request_body_with_nested_non_snake_case_fields(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """验证 requestBody 嵌套对象内的非 snake_case 字段同样自动添加 ``alias``。

        回归测试：``datamodel-code-generator`` 对每一层嵌套对象独立应用
        ``snake_case_field`` 转换，所有非 snake_case 字段（包括嵌套层）都
        必须携带 ``alias=<origin>``，否则反序列化 API 实际载荷时会丢失字段。
        """
        spec = """\
openapi: 3.1.0
info:
  title: Nested Non-Snake API
  version: "1.0.0"
paths:
  /orders:
    post:
      operationId: createOrder
      summary: 创建订单（嵌套对象含非蛇形字段）
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [customerInfo]
              properties:
                customerInfo:
                  type: object
                  required: [firstName]
                  properties:
                    firstName:
                      type: string
                    lastName:
                      type: string
                    billingAddress:
                      type: object
                      properties:
                        streetName:
                          type: string
                        ZIPCode:
                          type: string
                totalAmount:
                  type: number
      responses:
        "200":
          description: ok
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        models = (out_dir / "models.py").read_text(encoding="utf-8")

        # 顶层非 snake_case 字段加 alias。
        assert 'customer_info: CustomerInfo = Field(..., alias="customerInfo")' in models
        assert 'total_amount: float | None = Field(None, alias="totalAmount")' in models
        # 嵌套对象独立生成 model，字段同样满足 alias 约定。
        assert 'first_name: str = Field(..., alias="firstName")' in models
        assert 'last_name: str | None = Field(None, alias="lastName")' in models
        # 嵌套内的嵌套（含全大写字段名）也命中 alias。
        assert 'street_name: str | None = Field(None, alias="streetName")' in models
        assert 'zip_code: str | None = Field(None, alias="ZIPCode")' in models
