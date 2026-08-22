"""``src.openapi.renderer`` 端到端单元测试（通过 CLI 验证 route.py 生成结果）。

合并自以下历史文件：

- :mod:`tests.unit.test_cli.test_request_body` —— ``$ref`` / inline / 嵌套 / 数组 /
  空 body / ``embed=True`` / 非 PascalCase ref / kebab-case schema name /
  discriminator union / 无 operationId 报错 / 非 snake_case 字段 alias / 嵌套
  非 snake_case alias / oneOf / anyOf / allOf / request+response 共用模型 import 去重。
- :mod:`tests.unit.test_cli.test_request_body_form_multipart` —— form-urlencoded
  标量 / 数组 / 非 snake_case 字段、multipart 单文件 / Form+file 混合 / 标量
  JSON integer/string、binary octet-stream / image/png / 非 snake_case 字段
  warning、多 media_type 报错。
- :mod:`tests.unit.test_cli.test_response_body` —— ``$ref`` / 数组 / 嵌套 /
  201 / 无 content / 非 snake_case / 嵌套非 snake_case / oneOf / anyOf /
  多 status 合并 / 重复 status 去重 / 混合 JSON 与 description-only / 全 description-only /
  3 status union / inline 多 status 计数器 / 混合 ``$ref`` 与 inline / 仅有 4xx/5xx
  JSON 响应生成 models + route import + parser 探测。

这些测试都通过 CLI ``src.cli:app`` 触发 ``renderer.py`` 全管线，
因此归到 ``test_renderer.py``（对应 :mod:`src.openapi.renderer`）。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel, ConfigDict

from stoma.cli import app
from stoma.openapi.models import Endpoint
from stoma.openapi.parser import make_openapi_parser
from stoma.openapi.renderer import (
    GenerationErrorKind,
    ResponseSpecDecl,
    make_endpoint_renderer,
    make_range_matcher,
    render_status_code_kwarg,
)
from stoma.openapi.version import Reference31

# ============================================================
# Request Body
# ============================================================


def _build_spec(path: str, method: str, operation_id: str, request_body_block: str) -> str:
    """构造一个包含 ``requestBody`` 的 OpenAPI 3.1 规范。"""
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

    def test_request_body_with_ref_schema(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证 requestBody 使用 ``$ref`` 引用的 schema 时能正常生成。"""
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
        assert (out_dir / "endpoints" / "create_user.py").exists()
        content = (out_dir / "endpoints" / "create_user.py").read_text(encoding="utf-8")
        # 生成的代码应该从 .models 导入 User（不再内联模型）。
        assert "from ..models import User" in content
        # $ref 指向的 schema 有 title，render 为 case 1：body: <title>
        assert "body: User" in content

    def test_request_body_v30_ref_detection(self, valid_v30_spec: Path) -> None:
        """验证 OpenAPI 3.0.x ``requestBody.content.application/json.schema.$ref`` 被 renderer 正确识别。

        直接走 ``make_openapi_parser`` + ``make_endpoint_renderer`` 而不绕道 CLI——
        绕开 ``datamodel-code-generator`` 的副产物，纯粹验证 renderer 对 3.0
        ``Reference30`` 实例的 ``isinstance(schema, self.Reference)`` 检测
        （factory 注入 ``Reference30`` 类到 ``EndpointRenderer.Reference``，3.1 / 3.0 不串类）。
        """
        parser = make_openapi_parser(valid_v30_spec)
        parser.load()
        endpoints = parser.get_endpoints()
        renderer = make_endpoint_renderer(parser.spec_version)
        create_user = next(ep for ep in endpoints if ep.operation_id == "createUser")
        _file_name, code = renderer.render(create_user)
        assert "from ..models import User" in code
        assert "body: User" in code

    def test_request_body_with_inline_object_schema(self, cli_runner: Any, tmp_path: Path) -> None:
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
        assert (out_dir / "endpoints" / "create_item.py").exists()
        content = (out_dir / "endpoints" / "create_item.py").read_text(encoding="utf-8")
        assert "@router.post" in content
        # 内联对象生成 CreateItemRequest 模型（operationId 派生，
        # ``createItem`` → ``CreateItemRequest``），由 ``use_operation_id_as_name=True`` 触发。
        assert "from ..models import CreateItemRequest" in content
        assert "body: CreateItemRequest" in content

    def test_request_body_with_nested_object_schema(self, cli_runner: Any, tmp_path: Path) -> None:
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
        content = (out_dir / "endpoints" / "create_order.py").read_text(encoding="utf-8")
        # 嵌套对象可以正常生成。
        assert "createOrder" in content or "create_order" in content
        assert "@router.post" in content

    def test_request_body_with_array_schema(self, cli_runner: Any, tmp_path: Path) -> None:
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
        assert (out_dir / "endpoints" / "create_batch.py").exists()

    def test_request_body_with_no_body(self, cli_runner: Any, tmp_path: Path) -> None:
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
        content = (out_dir / "endpoints" / "health.py").read_text(encoding="utf-8")
        assert "@router.get" in content

    def test_request_body_with_embed_true(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证 requestBody 使用 ``embed=True``（单属性 wrapper）时生成 ``Body(embed=True)``。"""
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
        assert (out_dir / "endpoints" / "create_user_embed.py").exists()
        content = (out_dir / "endpoints" / "create_user_embed.py").read_text(encoding="utf-8")
        # 按 operationId 派生（``createUserEmbed`` → ``CreateUserEmbedRequest``），
        # 由 ``use_operation_id_as_name=True`` 触发。
        # body 形态由 spec 决定。
        assert "body: CreateUserEmbedRequest" in content
        assert "from ..models import CreateUserEmbedRequest" in content
        # JSON body 由 Playwright 自动派生 Content-Type，renderer 不注入 Header
        assert "from stoma import APIRoute" in content

    def test_request_body_with_non_pascalcase_ref(self, cli_runner: Any, tmp_path: Path) -> None:
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
        assert (out_dir / "endpoints" / "create_profile.py").exists()
        content = (out_dir / "endpoints" / "create_profile.py").read_text(encoding="utf-8")
        # ref 末段 ``user-profile`` 必须 PascalCase 为 ``UserProfile``，与
        # ``datamodel-code-generator`` 对 ``components.schemas`` key 的处理对齐。
        assert "from ..models import UserProfile" in content
        assert "body: UserProfile" in content

    def test_request_body_with_kebab_case_schema_name(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证 ``components.schemas`` key 含连字符（kebab-case）时与 dmcg 一致 PascalCase 化。

        回归测试：``components.schemas.user-profile``（含连字符）在
        ``datamodel-code-generator`` 中会被自动归一化为 ``class UserProfile``，
        stoma 的 renderer 必须使用同一归一化结果（``UserProfile``）作为
        ``from .models import`` 和 ``body:`` 的类型名，否则 route.py 与
        models.py 之间会出现 ImportError。
        """
        spec = """\
openapi: 3.1.0
info:
  title: Kebab Case Schema API
  version: "1.0.0"
paths:
  /users:
    post:
      operationId: createUser
      summary: 创建用户
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
      required: [display_name, age]
      properties:
        display_name:
          type: string
        age:
          type: integer
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        assert (out_dir / "endpoints" / "create_user.py").exists()
        assert (out_dir / "models.py").exists()

        models_content = (out_dir / "models.py").read_text(encoding="utf-8")
        assert "class UserProfile(BaseModel):" in models_content
        assert "class user-profile" not in models_content

        route_content = (out_dir / "endpoints" / "create_user.py").read_text(encoding="utf-8")
        assert "from ..models import UserProfile" in route_content
        assert "body: UserProfile" in route_content

    def test_request_body_with_discriminator_union(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证 requestBody 使用带 discriminator 的 ``oneOf`` schema 时生成联合模型。

        回归测试：discriminator oneOf 在 dmcg 0.72.2 中会生成
        ``RootModel[Cat | Dog]`` 作为 ``Pet``，并把 ``Cat`` / ``Dog`` 独立为可被
        ``Pet`` 引用的子类。路由文件应引用 ``Pet`` 作为 body 参数。
        """
        spec = """\
openapi: 3.1.0
info:
  title: Pet API
  version: "1.0.0"
paths:
  /pets:
    post:
      operationId: createPet
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/Pet'
      responses:
        "200":
          description: ok
components:
  schemas:
    Pet:
      oneOf:
        - $ref: '#/components/schemas/Cat'
        - $ref: '#/components/schemas/Dog'
      discriminator:
        propertyName: petType
        mapping:
          cat: '#/components/schemas/Cat'
          dog: '#/components/schemas/Dog'
    Cat:
      allOf:
        - $ref: '#/components/schemas/PetBase'
      properties:
        huntingSkill:
          type: string
    Dog:
      allOf:
        - $ref: '#/components/schemas/PetBase'
      properties:
        packSize:
          type: integer
    PetBase:
      type: object
      required: [petType, name]
      properties:
        petType:
          type: string
        name:
          type: string
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        models = (out_dir / "models.py").read_text(encoding="utf-8")
        route = (out_dir / "endpoints" / "create_pet.py").read_text(encoding="utf-8")
        assert "class Pet(RootModel[Cat | Dog])" in models
        assert "class Cat(PetBase)" in models
        assert "class Dog(PetBase)" in models
        assert 'Annotated[Cat | Dog, Field(discriminator="pet_type")]' in models
        assert "from ..models import Pet" in route
        assert "body: Pet" in route

    def test_request_body_without_operation_id_errors(self, cli_runner: Any, tmp_path: Path) -> None:
        """``operationId`` 必填校验——缺 ``operationId`` 时 CLI 应清晰报错而不是 fallback 到 method+path。

        回归测试：``parser.validate_operation_ids()`` 检查到缺失 ``operationId`` 时
        抛出 ``OpenAPISchemaError``，``cli.py`` 的 typer 错误处理器将其转换为
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

    def test_request_body_with_non_snake_case_fields(self, cli_runner: Any, tmp_path: Path) -> None:
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
        assert 'first_name: Annotated[str, Field(alias="firstName")]' in models
        assert 'is_active: Annotated[bool | None, Field(alias="isActive")] = None' in models
        # PascalCase → snake + alias 保留原名。
        assert 'last_name: Annotated[str, Field(alias="LastName")]' in models
        assert 'email_address: Annotated[EmailStr | None, Field(alias="EmailAddress")] = None' in models
        # 已 snake_case → 保持裸声明，不冗余加 alias。
        assert "user_id: str | None = None" in models
        assert 'user_id: str | None = Field(None, alias="user_id")' not in models

    def test_request_body_with_nested_non_snake_case_fields(self, cli_runner: Any, tmp_path: Path) -> None:
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
        assert 'customer_info: Annotated[CustomerInfo, Field(alias="customerInfo")]' in models
        assert 'total_amount: Annotated[float | None, Field(alias="totalAmount")] = None' in models
        # 嵌套对象独立生成 model，字段同样满足 alias 约定。
        assert 'first_name: Annotated[str, Field(alias="firstName")]' in models
        assert 'last_name: Annotated[str | None, Field(alias="lastName")] = None' in models
        # 嵌套内的嵌套（含全大写字段名）也命中 alias。
        assert 'street_name: Annotated[str | None, Field(alias="streetName")] = None' in models
        assert 'zip_code: Annotated[str | None, Field(alias="ZIPCode")] = None' in models

    def test_request_body_with_oneof_union(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证 requestBody 使用 ``oneOf`` 包含多个 ``$ref`` 时生成 Pydantic v2 联合类型。

        dmcg 0.72.2 在 ``use_union_operator=True``（默认）下为 ``oneOf`` 生成
        ``RootModel[TypeA | TypeB]``，其中 ``TypeA | TypeB`` 为内置 union 语法。
        ``route.py`` 应正确引用该 body 类型。
        """
        spec = _build_spec(
            "/entities",
            "post",
            "createEntity",
            """\
        required: true
        content:
          application/json:
            schema:
              oneOf:
                - $ref: '#/components/schemas/TypeA'
                - $ref: '#/components/schemas/TypeB'
components:
  schemas:
    TypeA:
      type: object
      required: [id]
      properties:
        id:
          type: string
        name_a:
          type: string
    TypeB:
      type: object
      required: [id]
      properties:
        id:
          type: string
        name_b:
          type: string
""",
        )
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        assert (out_dir / "models.py").exists()
        assert (out_dir / "endpoints" / "create_entity.py").exists()

        models_content = (out_dir / "models.py").read_text(encoding="utf-8")
        # dmcg 生成 RootModel[TypeA | TypeB]，验证 TypeA | TypeB 存在。
        assert "TypeA | TypeB" in models_content

        route_content = (out_dir / "endpoints" / "create_entity.py").read_text(encoding="utf-8")
        # route.py 应从 models 导入 body 类型。
        assert "from ..models import" in route_content
        assert "body:" in route_content

    def test_request_body_with_anyof_union(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证 requestBody 使用 ``anyOf`` 包含多个 ``$ref`` 时生成 Pydantic v2 联合类型。

        dmcg 0.72.2 在 ``use_union_operator=True``（默认）下为 ``anyOf`` 生成
        ``RootModel[TypeA | TypeB]``，与 ``oneOf`` 行为一致。route.py 应正确引用
        该 body 类型。
        """
        spec = _build_spec(
            "/records",
            "post",
            "createRecord",
            """\
        required: true
        content:
          application/json:
            schema:
              anyOf:
                - $ref: '#/components/schemas/TypeA'
                - $ref: '#/components/schemas/TypeB'
components:
  schemas:
    TypeA:
      type: object
      required: [id]
      properties:
        id:
          type: string
        kind_a:
          type: string
    TypeB:
      type: object
      required: [id]
      properties:
        id:
          type: string
        kind_b:
          type: string
""",
        )
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        assert (out_dir / "models.py").exists()
        assert (out_dir / "endpoints" / "create_record.py").exists()

        models_content = (out_dir / "models.py").read_text(encoding="utf-8")
        # dmcg 生成 RootModel[TypeA | TypeB]，验证 TypeA | TypeB 存在。
        assert "TypeA | TypeB" in models_content

        route_content = (out_dir / "endpoints" / "create_record.py").read_text(encoding="utf-8")
        # route.py 应从 models 导入 body 类型。
        assert "from ..models import" in route_content
        assert "body:" in route_content

    def test_request_body_with_allof_merge(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证 requestBody 使用 ``allOf`` 合并 ``$ref`` 父 schema 与内联对象时字段被正确合并。

        dmcg 0.72.2 通过 Python 类继承实现 ``allOf`` 合并：父类保留 ``$ref`` 指向
        的字段（``BaseModelModel`` 是 dmcg 对 ``BaseModel`` schema 的自动重命名结果，
        避免与 ``pydantic.BaseModel`` 冲突），子类由 ``use_operation_id_as_name=True``
        从 ``createOrder`` 派生出 ``CreateOrderRequest``，继承父类并新增内联
        ``extra`` 字段。``route.py`` 通过 ``body: CreateOrderRequest`` 引用合并后
        的类型，运行时请求体验证同时覆盖父类字段与内联字段。
        """
        spec = """\
openapi: 3.1.0
info:
  title: allOf Merge API
  version: "1.0.0"
paths:
  /orders:
    post:
      operationId: createOrder
      summary: 创建订单（allOf 合并）
      requestBody:
        required: true
        content:
          application/json:
            schema:
              allOf:
                - $ref: '#/components/schemas/BaseModel'
                - type: object
                  properties:
                    extra:
                      type: string
      responses:
        "200":
          description: ok
components:
  schemas:
    BaseModel:
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
        assert (out_dir / "models.py").exists()
        assert (out_dir / "endpoints" / "create_order.py").exists()

        models = (out_dir / "models.py").read_text(encoding="utf-8")
        # ``createOrder`` 经 ``use_operation_id_as_name=True`` 派生出合并类型
        # ``CreateOrderRequest``，dmcg 通过 Python 类继承实现 ``allOf`` 合并。
        assert "class CreateOrderRequest(" in models
        # 父类 ``BaseModelModel``（dmcg 对 ``BaseModel`` 的自动重命名）保留 ``id`` 字段。
        assert "class BaseModelModel(" in models
        # 内联 ``allOf`` 对象新增的 ``extra`` 字段被合入子类。
        assert "extra:" in models
        # 父类的 ``id`` 字段在 ``models.py`` 中触达（transitively via inheritance）。
        assert "id: str" in models

        route = (out_dir / "endpoints" / "create_order.py").read_text(encoding="utf-8")
        # route 引用合并后的 ``CreateOrderRequest``，请求体验证覆盖父类 + 内联字段。
        assert "from ..models import CreateOrderRequest" in route
        assert "body: CreateOrderRequest" in route

    def test_request_and_response_share_model_dedupes_import(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证 requestBody 和 response 共用同一 schema 时 import 不重复。

        回归测试：当 ``POST /users`` 的 ``requestBody`` 和 ``201`` ``response`` 都引用
        ``$ref: '#/components/schemas/User'`` 时，renderer 必须对
        ``imported_models`` 去重，避免生成 ``from .models import User, User``
        这种语法错误的重复导入。
        """
        spec = """\
openapi: 3.1.0
info:
  title: Shared Model API
  version: "1.0.0"
paths:
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
          description: 创建成功
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
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        route_content = (out_dir / "endpoints" / "create_user.py").read_text(encoding="utf-8")
        # 导入了 User（存在至少一次）。
        assert "from ..models import User" in route_content
        # 不应该出现重复的 ``User, User``。
        assert "from ..models import User, User" not in route_content
        # 文件必须是语法正确的 Python。
        compile(route_content, "create_user.py", "exec")


# ============================================================
# Class Body `pass` Sentinel
# ============================================================


class TestClassBodyPass:
    """验证 class body `pass` 占位逻辑：仅在 body 完全为空（无 docstring + 无字段）时插入 `pass`。"""

    def test_empty_class_body_inserts_pass(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证 endpoint 无 docstring（无 summary/description）、无 requestBody、无 parameters 时 class body 插入 ``pass``。"""
        spec = """\
openapi: 3.1.0
info:
  title: Empty Body API
  version: "1.0.0"
paths:
  /items:
    get:
      operationId: listItems
      responses:
        "200":
          description: ok
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "endpoints" / "list_items.py").read_text(encoding="utf-8")
        # body 为空且无 docstring 时应插入 pass 占位
        assert "\n    pass\n" in content or "\n    pass" in content
        compile(content, "list_items.py", "exec")

    def test_class_body_with_header_fields_no_pass(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证 endpoint 有 header 参数（无 docstring）时 class body 不插入 ``pass``。

        Regression test: Phase 5 secondary bug — ``pass`` 被错误插入到有字段的 class body 开头。
        """
        spec = """\
openapi: 3.1.0
info:
  title: Header Params API
  version: "1.0.0"
paths:
  /profile:
    get:
      operationId: getProfile
      parameters:
        - name: X-Request-ID
          in: header
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

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "endpoints" / "get_profile.py").read_text(encoding="utf-8")
        # class body 有 header 字段时不应有 pass（bug 场景）
        # pass 应该在 header 字段之前，而不是替代它
        assert "    pass\n    x_request_id:" not in content
        assert "x_request_id:" in content
        compile(content, "get_profile.py", "exec")


# ============================================================
# Request Body — Form / Multipart / Scalar / Binary
# ============================================================


_CONTENT_TYPE_LINE_TEMPLATE: str = (
    'content_type: Annotated[str, Header(), Field(serialization_alias="Content-Type")] = "{media_type}"'
)


def _content_type_line(media_type: str) -> str:
    """生成 auto Content-Type 字段声明的完整字符串。"""
    return _CONTENT_TYPE_LINE_TEMPLATE.format(media_type=media_type)


def _build_spec_with_components(
    path: str,
    method: str,
    operation_id: str,
    request_body_block: str,
    components_block: str = "",
) -> str:
    """构造一个包含 ``requestBody`` 的 OpenAPI 3.1 规范（含 components 块可选）。"""
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
{components_block}
"""


class TestMakeRequestBodyFormMultipart:
    """测试 form-urlencoded / multipart / scalar JSON / binary 请求体的生成结果。"""

    def test_form_urlencoded_scalar(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证 ``application/x-www-form-urlencoded`` 单标量字段生成 ``Annotated[str, Form()]``。

        Content-Type 由 Playwright 根据 ``form`` 参数自动派生，renderer 不注入。
        """
        spec = _build_spec_with_components(
            "/login",
            "post",
            "loginUser",
            """\
        required: true
        content:
          application/x-www-form-urlencoded:
            schema:
              type: object
              properties:
                username:
                  type: string
                password:
                  type: string
""",
        )
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "endpoints" / "login_user.py").read_text(encoding="utf-8")
        assert "username: Annotated[str, Form()]" in content
        assert "password: Annotated[str, Form()]" in content
        assert "from stoma import APIRoute, Form" in content
        # 无 auto Content-Type，Playwright 自己设置
        assert "content_type" not in content
        compile(content, "login_user.py", "exec")

    def test_form_urlencoded_array(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证 form-urlencoded 含数组字段时派生 ``list[T]``（从 ``items.type`` 取元素类型）。"""
        spec = _build_spec_with_components(
            "/tags",
            "post",
            "addTags",
            """\
        required: true
        content:
          application/x-www-form-urlencoded:
            schema:
              type: object
              properties:
                tags:
                  type: array
                  items:
                    type: string
""",
        )
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "endpoints" / "add_tags.py").read_text(encoding="utf-8")
        # 数组字段从 items.type 派生 list[T];与 runtime Annotated[list[str], Form()] 一致
        assert "tags: Annotated[list[str], Form()]" in content
        assert "from stoma import APIRoute, Form" in content
        assert "content_type" not in content
        compile(content, "add_tags.py", "exec")

    def test_form_urlencoded_array_with_int_items(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证 form-urlencoded 数组字段以 ``items.type`` 为元素类型派生 ``list[int]``。"""
        spec = _build_spec_with_components(
            "/scores",
            "post",
            "addScores",
            """\
        required: true
        content:
          application/x-www-form-urlencoded:
            schema:
              type: object
              properties:
                scores:
                  type: array
                  items:
                    type: integer
""",
        )
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "endpoints" / "add_scores.py").read_text(encoding="utf-8")
        # items.type=integer → list[int]
        assert "scores: Annotated[list[int], Form()]" in content
        assert "from stoma import APIRoute, Form" in content
        assert "content_type" not in content
        compile(content, "add_scores.py", "exec")

    def test_multipart_single_file(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证 ``multipart/form-data`` 含 ``format: binary`` 单文件字段生成 UploadFile（无 Form import）。

        Content-Type（含 boundary）由 Playwright 自动设置，renderer 不注入。
        """
        spec = _build_spec_with_components(
            "/upload",
            "post",
            "uploadAvatar",
            """\
        required: true
        content:
          multipart/form-data:
            schema:
              type: object
              properties:
                avatar:
                  type: string
                  format: binary
""",
        )
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "endpoints" / "upload_avatar.py").read_text(encoding="utf-8")
        assert "avatar: UploadFile" in content
        assert "from stoma import APIRoute, UploadFile" in content
        # 无 auto Content-Type，Playwright 自己设置
        assert "content_type" not in content
        # multipart 文件场景不应导入 Form
        assert "Form" not in content
        compile(content, "upload_avatar.py", "exec")

    def test_multipart_form_file_mix(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证 ``multipart/form-data`` 混合标量 + binary 字段同时生成 Form 和 UploadFile。

        Content-Type（含 boundary）由 Playwright 自动设置，renderer 不注入。
        """
        spec = _build_spec_with_components(
            "/upload-mix",
            "post",
            "uploadWithForm",
            """\
        required: true
        content:
          multipart/form-data:
            schema:
              type: object
              properties:
                username:
                  type: string
                avatar:
                  type: string
                  format: binary
""",
        )
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "endpoints" / "upload_with_form.py").read_text(encoding="utf-8")
        assert "username: Annotated[str, Form()]" in content
        assert "avatar: UploadFile" in content
        assert "from stoma import APIRoute, Form, UploadFile" in content
        assert "content_type" not in content
        compile(content, "upload_with_form.py", "exec")

    def test_scalar_json_integer(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证 ``application/json`` 含 integer scalar schema 生成 ``body: Annotated[int, Body(media_type='application/json')]``。

        字段名固定为 ``body``（不受 ``operation_id`` 是否 snake_case 影响），避免
        非 snake_case 时追加 ``Field(serialization_alias=...)`` 的副作用。
        Content-Type 由 ``Body(media_type=...)`` 提供，renderer 不生成 Header field。
        """
        spec = _build_spec_with_components(
            "/importance",
            "post",
            "setImportance",
            """\
        required: true
        content:
          application/json:
            schema:
              type: integer
""",
            components_block="""\
components:
  schemas:
    _Dummy:
      type: object
      properties:
        dummy:
          type: string
""",
        )
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "endpoints" / "set_importance.py").read_text(encoding="utf-8")
        # scalar body 字段名固定 body，media_type 嵌入 Body(media_type=...)
        assert 'body: Annotated[int, Body(media_type="application/json")]' in content
        assert "from stoma import APIRoute, Body" in content
        # scalar 走 Body(media_type=...) 路径，不生成 Content-Type Header field
        assert "content_type" not in content
        compile(content, "set_importance.py", "exec")

    def test_scalar_json_string(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证 ``application/json`` 含 string scalar schema 生成 ``body: Annotated[str, Body(media_type='application/json')]``。

        字段名固定为 ``body``（不受 ``operation_id`` 是否 snake_case 影响）。
        Content-Type 由 ``Body(media_type=...)`` 提供，renderer 不生成 Header field。
        """
        spec = _build_spec_with_components(
            "/scalar",
            "post",
            "postScalar",
            """\
        required: true
        content:
          application/json:
            schema:
              type: string
""",
            components_block="""\
components:
  schemas:
    _Dummy:
      type: object
      properties:
        dummy:
          type: string
""",
        )
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "endpoints" / "post_scalar.py").read_text(encoding="utf-8")
        assert 'body: Annotated[str, Body(media_type="application/json")]' in content
        assert "from stoma import APIRoute, Body" in content
        # scalar 走 Body(media_type=...) 路径，不生成 Content-Type Header field
        assert "content_type" not in content
        compile(content, "post_scalar.py", "exec")

    def test_binary_octet_stream(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证 ``application/octet-stream`` 生成 ``body: UploadFile`` + ``upload_as_multipart=False``。

        字段名固定为 ``body``（不受 ``operation_id`` 是否 snake_case 影响）。
        """
        spec = _build_spec_with_components(
            "/raw",
            "post",
            "uploadRaw",
            """\
        required: true
        content:
          application/octet-stream:
            schema:
              type: string
              format: binary
""",
        )
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "endpoints" / "upload_raw.py").read_text(encoding="utf-8")
        assert "body: UploadFile" in content
        assert "upload_as_multipart=False" in content
        # auto Content-Type header 触发 Header + Field import
        assert "from pydantic import Field" in content
        assert "from stoma import APIRoute, Header, UploadFile" in content
        assert _content_type_line("application/octet-stream") in content
        compile(content, "upload_raw.py", "exec")

    def test_binary_image_png(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证 ``image/png`` 生成 ``body: UploadFile`` + ``upload_as_multipart=False``。

        字段名固定为 ``body``。
        """
        spec = _build_spec_with_components(
            "/image",
            "post",
            "uploadImage",
            """\
        required: true
        content:
          image/png:
            schema:
              type: string
              format: binary
""",
        )
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "endpoints" / "upload_image.py").read_text(encoding="utf-8")
        assert "body: UploadFile" in content
        assert "upload_as_multipart=False" in content
        # auto Content-Type header 触发 Header + Field import
        assert "from pydantic import Field" in content
        assert "from stoma import APIRoute, Header, UploadFile" in content
        assert _content_type_line("image/png") in content
        compile(content, "upload_image.py", "exec")

    def test_form_urlencoded_non_snake_case_field(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证 urlencoded form 字段名非 snake_case 时自动加 ``Field(serialization_alias=...)`` 保留原名。"""
        spec = _build_spec_with_components(
            "/submit",
            "post",
            "submitForm",
            """\
        required: true
        content:
          application/x-www-form-urlencoded:
            schema:
              type: object
              properties:
                user-name:
                  type: string
                X-API-Key:
                  type: string
""",
        )
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "endpoints" / "submit_form.py").read_text(encoding="utf-8")
        # 非 snake_case 字段自动加 serialization_alias 保留原名
        assert 'user_name: Annotated[str, Form(), Field(serialization_alias="user-name")]' in content
        assert 'x_api_key: Annotated[str, Form(), Field(serialization_alias="X-API-Key")]' in content
        compile(content, "submit_form.py", "exec")

    def test_multipart_form_non_snake_case_field(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证 multipart form 标量字段非 snake_case 时同样加 ``Field(serialization_alias=...)``。"""
        spec = _build_spec_with_components(
            "/upload-attrs",
            "post",
            "uploadWithAttrs",
            """\
        required: true
        content:
          multipart/form-data:
            schema:
              type: object
              properties:
                user-name:
                  type: string
                file:
                  type: string
                  format: binary
""",
        )
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "endpoints" / "upload_with_attrs.py").read_text(encoding="utf-8")
        # multipart 标量字段非 snake_case 时加 alias
        assert 'user_name: Annotated[str, Form(), Field(serialization_alias="user-name")]' in content
        # file 字段保持裸 UploadFile（无 alias）
        assert "file: UploadFile" in content
        compile(content, "upload_with_attrs.py", "exec")

    def test_urlencoded_form_binary_field_emits_warning(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证 urlencoded form 含 ``format=binary`` 字段时 emit ``UserWarning``（不抛错）。"""
        spec = _build_spec_with_components(
            "/mixed-bad",
            "post",
            "submitMixed",
            """\
        required: true
        content:
          application/x-www-form-urlencoded:
            schema:
              type: object
              properties:
                username:
                  type: string
                avatar:
                  type: string
                  format: binary
""",
        )
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        with pytest.warns(UserWarning, match="format=binary"):
            result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        # CLI 仍正常退出，form 字段被渲染
        assert result.exit_code == 0, result.output
        content = (out_dir / "endpoints" / "submit_mixed.py").read_text(encoding="utf-8")
        assert "username: Annotated[str, Form()]" in content
        # urlencoded binary 字段退化为 form 标量（不再引发额外 side-effect）
        assert "avatar: Annotated[str, Form()]" in content
        compile(content, "submit_mixed.py", "exec")

    def test_multiple_media_types_silently_picks_first(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证 ``requestBody`` 含多个 media type 时静默选第一个 + stderr 报告警告（不自举报错）。

        对应 commit 857e1b3：多 media type 行为从「抛错中断」改为「静默选第一个 + 报告到 stderr」。
        """
        spec = _build_spec_with_components(
            "/ambiguous",
            "post",
            "ambiguousBody",
            """\
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                name:
                  type: string
          multipart/form-data:
            schema:
              type: object
              properties:
                file:
                  type: string
                  format: binary
""",
        )
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        assert "多个 media type" in result.stderr or "multiple media type" in result.stderr.lower()
        assert "POST /ambiguous" in result.stderr
        route_file = out_dir / "endpoints" / "ambiguous_body.py"
        assert route_file.exists(), f"route 文件未生成: {route_file}"
        content = route_file.read_text(encoding="utf-8")
        assert "AmbiguousBodyRequest" in content
        compile(content, "ambiguous_body.py", "exec")

    def test_multipart_file_field_non_snake_case_property(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证 multipart file property 名非 snake_case 时自动加 ``Field(serialization_alias=...)``。

        对应第三轮 follow-up ⑥：``_build_upload_file_field_line`` 现在对非 snake_case
        字段名追加 ``Field(serialization_alias=<origin>)``，与 form 标量字段一致。
        """
        spec = _build_spec_with_components(
            "/upload-non-snake",
            "post",
            "uploadNonSnake",
            """\
        required: true
        content:
          multipart/form-data:
            schema:
              type: object
              properties:
                avatar-file:
                  type: string
                  format: binary
""",
        )
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "endpoints" / "upload_non_snake.py").read_text(encoding="utf-8")
        assert 'avatar_file: Annotated[UploadFile, Field(serialization_alias="avatar-file")]' in content
        assert "from pydantic import Field" in content
        assert "from stoma import APIRoute, UploadFile" in content
        assert "content_type" not in content
        compile(content, "upload_non_snake.py", "exec")

    def test_binary_non_snake_case_operation_id(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证 binary body 字段名固定为 ``body``，不受 ``operation_id`` snake_case 影响。

        原行为：按 ``operation_id`` 派生 field name，非 snake_case 时追加
        ``Field(serialization_alias=<origin>)``。新行为：固定 ``body: UploadFile``，
        无 alias。
        """
        spec = _build_spec_with_components(
            "/file",
            "post",
            "uploadFile",
            """\
        required: true
        content:
          application/octet-stream:
            schema:
              type: string
              format: binary
""",
        )
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "endpoints" / "upload_file.py").read_text(encoding="utf-8")
        assert "body: UploadFile" in content
        assert "upload_as_multipart=False" in content
        # auto Content-Type header 触发 Header + Field import
        assert "from pydantic import Field" in content
        assert "from stoma import APIRoute, Header, UploadFile" in content
        compile(content, "upload_file.py", "exec")


# ============================================================
# Response Body
# ============================================================


class TestMakeResponseBody:
    """测试各种 response body 场景的生成结果。"""

    def test_response_with_ref_schema(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证 response 使用 ``$ref`` 引用的 schema 时生成对应模型。"""
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
        content = (out_dir / "endpoints" / "get_user.py").read_text(encoding="utf-8")
        assert "on_200: ClassVar[JSONResponseSpec]" in content
        assert "model=User" in content
        assert "from ..models import User" in content
        assert "APIRoute[" not in content

    def test_response_body_v30_ref_detection(self, valid_v30_spec: Path) -> None:
        """验证 OpenAPI 3.0.x ``responses[200].content.application/json.schema.$ref`` 被 renderer 正确识别。

        直接走 ``make_openapi_parser`` + ``make_endpoint_renderer`` 而不绕道 CLI——
        绕开 ``datamodel-code-generator`` 的副产物，纯粹验证 renderer 对 3.0
        ``Reference30`` 实例的 ``isinstance(schema, self.Reference)`` 检测
        （factory 注入 ``Reference30`` 类到 ``EndpointRenderer.Reference``，3.1 / 3.0 不串类）。
        """
        parser = make_openapi_parser(valid_v30_spec)
        parser.load()
        endpoints = parser.get_endpoints()
        renderer = make_endpoint_renderer(parser.spec_version)
        get_user = next(ep for ep in endpoints if ep.operation_id == "getUser")
        _file_name, code = renderer.render(get_user)
        assert "from ..models import User" in code
        assert "on_200: ClassVar[JSONResponseSpec]" in code
        assert "model=User" in code
        assert "APIRoute[" not in code

    def test_response_with_array_of_ref(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证 response 为引用类型的数组时生成 ``list[Model]``。"""
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
        content = (out_dir / "endpoints" / "list_users.py").read_text(encoding="utf-8")
        assert "on_200: ClassVar[JSONResponseSpec]" in content
        assert "model=ListUsersResponse" in content
        assert "from ..models import ListUsersResponse" in content
        assert "APIRoute[" not in content

    def test_response_with_nested_object_schema(self, cli_runner: Any, tmp_path: Path) -> None:
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
        assert (out_dir / "endpoints" / "get_profile.py").exists()
        content = (out_dir / "endpoints" / "get_profile.py").read_text(encoding="utf-8")
        assert "@router.get" in content
        assert "on_200: ClassVar[JSONResponseSpec]" in content
        assert "model=GetProfileResponse" in content
        assert "from ..models import GetProfileResponse" in content
        assert "APIRoute[" not in content

    def test_response_201_uses_201_status(self, cli_runner: Any, tmp_path: Path) -> None:
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
        content = (out_dir / "endpoints" / "create_user.py").read_text(encoding="utf-8")
        assert "on_201: ClassVar[JSONResponseSpec]" in content
        assert "model=User" in content
        assert "APIRoute[" not in content

    def test_response_without_content(self, cli_runner: Any, tmp_path: Path) -> None:
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
        content = (out_dir / "endpoints" / "delete_item.py").read_text(encoding="utf-8")
        # 无 content-type 为 json 的响应，不生成泛型参数。
        assert "APIRoute)" in content

    def test_response_with_non_snake_case_fields(self, cli_runner: Any, tmp_path: Path) -> None:
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
        assert 'widget_id: Annotated[str, Field(alias="widgetId")]' in models
        assert 'widget_name: Annotated[str, Field(alias="widgetName")]' in models
        # PascalCase → snake + alias 保留原名。
        assert 'created_at: Annotated[AwareDatetime | None, Field(alias="CreatedAt")] = None' in models
        # 已 snake_case → 保持裸声明，不冗余加 alias。
        assert "item_count: int | None = None" in models
        assert 'item_count: int | None = Field(None, alias="item_count")' not in models

    def test_response_with_nested_non_snake_case_fields(self, cli_runner: Any, tmp_path: Path) -> None:
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
        assert 'order_info: Annotated[OrderInfo, Field(alias="orderInfo")]' in models
        assert 'total_amount: Annotated[float | None, Field(alias="totalAmount")] = None' in models
        # 嵌套对象独立生成 model，字段同样满足 alias 约定。
        assert 'order_id: Annotated[str, Field(alias="orderId")]' in models
        # 嵌套内的嵌套（含全大写字段名）也命中 alias。
        assert 'street_name: Annotated[str | None, Field(alias="streetName")] = None' in models
        assert 'zip_code: Annotated[str | None, Field(alias="ZIPCode")] = None' in models

    def test_response_with_oneof_union(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证 response 使用 ``oneOf`` 引用多个 schema 时生成 union 类型。

        dmcg 对 response oneOf 包装为 ``RootModel[TypeA | TypeB]``，
        由 ``use_operation_id_as_name=True`` 派生响应模型名
        （``getEntity`` → ``GetEntityResponse``）。
        """
        spec = """\
openapi: 3.1.0
info:
  title: Response OneOf Union API
  version: "1.0.0"
paths:
  /entity:
    get:
      operationId: getEntity
      summary: 获取实体
      responses:
        "200":
          description: ok
          content:
            application/json:
              schema:
                oneOf:
                  - $ref: '#/components/schemas/TypeA'
                  - $ref: '#/components/schemas/TypeB'
components:
  schemas:
    TypeA:
      type: object
      required: [id]
      properties:
        id:
          type: string
        name:
          type: string
    TypeB:
      type: object
      required: [id]
      properties:
        id:
          type: string
        value:
          type: integer
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        models = (out_dir / "models.py").read_text(encoding="utf-8")
        route = (out_dir / "endpoints" / "get_entity.py").read_text(encoding="utf-8")
        # dmcg 将 oneOf 包装为 RootModel[TypeA | TypeB]。
        assert "TypeA | TypeB" in models
        # 由 use_operation_id_as_name 派生响应包装类。
        assert "GetEntityResponse" in models
        assert "RootModel[TypeA | TypeB]" in models
        # route.py 正确引用包装类。
        assert "on_200: ClassVar[JSONResponseSpec]" in route
        assert "model=GetEntityResponse" in route
        assert "APIRoute[" not in route
        assert "from ..models import GetEntityResponse" in route

    def test_response_with_anyof_union(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证 response 使用 ``anyOf`` 引用多个 schema 时生成 union 类型。

        dmcg 对 response anyOf 包装为 ``RootModel[TypeA | TypeB]``，
        由 ``use_operation_id_as_name=True`` 派生响应模型名
        （``getRecord`` → ``GetRecordResponse``）。
        """
        spec = """\
openapi: 3.1.0
info:
  title: Response AnyOf Union API
  version: "1.0.0"
paths:
  /record:
    get:
      operationId: getRecord
      summary: 获取记录
      responses:
        "200":
          description: ok
          content:
            application/json:
              schema:
                anyOf:
                  - $ref: '#/components/schemas/TypeA'
                  - $ref: '#/components/schemas/TypeB'
components:
  schemas:
    TypeA:
      type: object
      required: [id]
      properties:
        id:
          type: string
        kind_a:
          type: string
    TypeB:
      type: object
      required: [id]
      properties:
        id:
          type: string
        kind_b:
          type: integer
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        models = (out_dir / "models.py").read_text(encoding="utf-8")
        route = (out_dir / "endpoints" / "get_record.py").read_text(encoding="utf-8")
        # dmcg 将 anyOf 包装为 RootModel[TypeA | TypeB]。
        assert "TypeA | TypeB" in models
        # 由 use_operation_id_as_name 派生响应包装类。
        assert "GetRecordResponse" in models
        assert "RootModel[TypeA | TypeB]" in models
        # route.py 正确引用包装类。
        assert "on_200: ClassVar[JSONResponseSpec]" in route
        assert "model=GetRecordResponse" in route
        assert "APIRoute[" not in route
        assert "from ..models import GetRecordResponse" in route

    def test_response_with_multiple_status_codes_union(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证 200 ``$ref: User`` + 404 ``$ref: Error`` 时 route 泛型合并成 Union。

        行为契约：

        - ``responses`` 字典按 OpenAPI spec 顺序收集所有 JSON status 的模型名。
        - 拼接为 PEP 604 ``A | B`` 形式作为 ``APIRoute[...]`` 泛型参数。
        - ``from .models import`` 行必须同时包含 ``User`` 和 ``Error``。
        - 顺序以 spec 里 status 的书写顺序为准（200 先于 404）。
        """
        spec = """\
openapi: 3.1.0
info:
  title: Multi-Status Union API
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
          description: not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'
components:
  schemas:
    User:
      type: object
      required: [id]
      properties:
        id:
          type: string
    Error:
      type: object
      required: [code]
      properties:
        code:
          type: string
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        route = (out_dir / "endpoints" / "get_user.py").read_text(encoding="utf-8")
        assert "on_200: ClassVar[JSONResponseSpec]" in route
        assert "on_404: ClassVar[JSONResponseSpec]" in route
        assert "model=User" in route
        assert "model=Error" in route
        assert "from ..models import Error, User" in route
        assert "APIRoute[" not in route

    def test_response_with_duplicate_status_codes_dedup(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证 200 ``$ref: User`` + 201 ``$ref: User`` 时 Union 去重。

        行为契约：

        - 同一模型名出现在多个 status 时，``APIRoute[...]`` 泛型里只出现一次。
        - ``from .models import`` 行只 import ``User`` 一次（不重复出现 ``User, User``）。
        - 不允许出现 ``User | User`` 这种无效自连接。
        """
        spec = """\
openapi: 3.1.0
info:
  title: Duplicate Status Dedup API
  version: "1.0.0"
paths:
  /users:
    post:
      operationId: createUser
      summary: 创建用户
      responses:
        "200":
          description: ok
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/User'
        "201":
          description: created
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
        route = (out_dir / "endpoints" / "create_user.py").read_text(encoding="utf-8")
        assert "on_200: ClassVar[JSONResponseSpec]" in route
        assert "on_201: ClassVar[JSONResponseSpec]" in route
        assert route.count("model=User") == 2
        assert "from ..models import User" in route
        assert route.count("from ..models import User") == 1
        assert "import User, User" not in route
        assert "APIRoute[" not in route

    def test_response_with_mixed_json_and_non_json_status(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证 200 JSON ``$ref: User`` + 400 description-only 时 Union 退化为单元素。

        行为契约：

        - 只有 ``application/json`` content 的 status 才参与 Union。
        - 仅含 ``description``（无 content）的 status 被跳过，不影响结果。
        - 结果是单元素 ``APIRoute[User]``，不是空 union 或错误拼接。
        """
        spec = """\
openapi: 3.1.0
info:
  title: Mixed JSON and Description-Only API
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
        "400":
          description: bad request
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
        route = (out_dir / "endpoints" / "get_user.py").read_text(encoding="utf-8")
        assert "on_200: ClassVar[JSONResponseSpec]" in route
        assert "model=User" in route
        assert "on_400" not in route
        assert "from ..models import User" in route
        assert "APIRoute[" not in route

    def test_response_with_only_non_json_status_codes(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证所有 status 都只有 description、无 ``application/json`` 时，route 保持裸 ``APIRoute)``。

        行为契约：

        - 所有 status 均无 ``application/json`` content（典型：纯 health check 接口）。
        - 不输出 ``APIRoute[...]`` 泛型语法，保持裸 ``APIRoute)``。
        - ``from .models import ...`` 行不出现（无响应模型需要 import）。
        """
        spec = """\
openapi: 3.1.0
info:
  title: Only Description-Only Status API
  version: "1.0.0"
paths:
  /health:
    get:
      operationId: healthCheck
      summary: 健康检查
      responses:
        "200":
          description: ok
        "204":
          description: no content
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        route = (out_dir / "endpoints" / "health_check.py").read_text(encoding="utf-8")
        # 裸 ``APIRoute)``，无泛型参数。
        assert "APIRoute)" in route
        # 不输出 ``APIRoute[...]`` 形式。
        assert "APIRoute[" not in route
        # 没有响应模型可 import，不应有 ``from .models import ...`` 行。
        assert "from ..models import" not in route

    def test_response_with_three_status_codes_union(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证 200 + 400 + 500 三个 ``$ref`` 都参与 Union，且 import 行三个都列出。

        行为契约：

        - 三个 JSON status 都进入 ``APIRoute[...]``，按 spec 顺序拼接成 pipe union。
        - ``from .models import ...`` 行包含全部三个模型名。
        - 验证不仅测首尾，中间元素 ``Error`` 也必须在两个断言里都出现。
        """
        spec = """\
openapi: 3.1.0
info:
  title: Three-Status Union API
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
        "400":
          description: bad request
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'
        "500":
          description: server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ServerError'
components:
  schemas:
    User:
      type: object
      required: [id]
      properties:
        id:
          type: string
    Error:
      type: object
      required: [code]
      properties:
        code:
          type: string
    ServerError:
      type: object
      required: [trace_id]
      properties:
        trace_id:
          type: string
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        route = (out_dir / "endpoints" / "get_user.py").read_text(encoding="utf-8")
        assert "on_200: ClassVar[JSONResponseSpec]" in route
        assert "on_400: ClassVar[JSONResponseSpec]" in route
        assert "on_500: ClassVar[JSONResponseSpec]" in route
        assert "model=User" in route
        assert "model=Error" in route
        assert "model=ServerError" in route
        assert "from ..models import Error, ServerError, User" in route
        assert "APIRoute[" not in route

    def test_response_with_inline_multi_status_uses_counter_suffix(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证多个 inline 响应用 dmcg 计数器后缀（``GetXResponse`` / ``GetXResponse1``）。

        行为契约：

        - dmcg 对多个 inline response 按 ``{OpId}Response`` / ``{OpId}Response1``
          计数器命名（``use_operation_id_as_name=True``）。
        - renderer 必须镜像同一规则，否则 inline 错误响应模型会被丢弃。
        - ``APIRoute[...]`` 同时引用 ``GetXResponse`` 和 ``GetXResponse1``。
        - ``from .models import ...`` 行同时列出两者。
        - 计数器从 1 开始（不是 0），与 dmcg ``openapi.py:_parse_schema_or_ref``
          inline 路径命名规则一致。
        """
        spec = """\
openapi: 3.1.0
info:
  title: Inline Multi-Status Counter API
  version: "1.0.0"
paths:
  /users/{user_id}:
    get:
      operationId: getX
      summary: 获取
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
                type: object
                required: [id]
                properties:
                  id:
                    type: string
        "400":
          description: bad request
          content:
            application/json:
              schema:
                type: object
                required: [code]
                properties:
                  code:
                    type: string
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        models = (out_dir / "models.py").read_text(encoding="utf-8")
        route = (out_dir / "endpoints" / "get_x.py").read_text(encoding="utf-8")
        assert "class GetXResponse" in models
        assert "class GetXResponse1" in models
        assert "class GetXResponse2" not in models
        assert "on_200: ClassVar[JSONResponseSpec]" in route
        assert "on_400: ClassVar[JSONResponseSpec]" in route
        assert "model=GetXResponse" in route
        assert "model=GetXResponse1" in route
        assert "from ..models import GetXResponse, GetXResponse1" in route
        assert "APIRoute[" not in route
        # import 行同时列出两者。
        assert "from ..models import GetXResponse, GetXResponse1" in route

    def test_response_with_mixed_ref_and_inline_multi_status(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证 200 ``$ref User`` + 400/500 inline 时 ``$ref`` 不消耗 inline 计数器。

        行为契约：

        - dmcg 对 ``$ref`` 走 ``resolve_ref`` 短路，inline 命名从 1 开始，不受 ``$ref`` 影响。
        - renderer 必须镜像：``$ref`` 不消耗 inline 计数器，inline 仍命名为
          ``GetXResponse`` / ``GetXResponse1``。
        - ``APIRoute[...]`` 顺序为 spec 出现顺序：``User`` (200) → ``GetXResponse`` (400) → ``GetXResponse1`` (500)。
        - import 行同步列出全部三个。
        """
        spec = """\
openapi: 3.1.0
info:
  title: Mixed Ref and Inline Multi-Status API
  version: "1.0.0"
paths:
  /users/{user_id}:
    get:
      operationId: getX
      summary: 获取
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
        "400":
          description: bad request
          content:
            application/json:
              schema:
                type: object
                required: [code]
                properties:
                  code:
                    type: string
        "500":
          description: server error
          content:
            application/json:
              schema:
                type: object
                required: [retry]
                properties:
                  retry:
                    type: boolean
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
        models = (out_dir / "models.py").read_text(encoding="utf-8")
        route = (out_dir / "endpoints" / "get_x.py").read_text(encoding="utf-8")
        assert "class GetXResponse" in models
        assert "class GetXResponse1" in models
        assert "class GetXResponse2" not in models
        assert "on_200: ClassVar[JSONResponseSpec]" in route
        assert "on_400: ClassVar[JSONResponseSpec]" in route
        assert "on_500: ClassVar[JSONResponseSpec]" in route
        assert "model=User" in route
        assert "model=GetXResponse" in route
        assert "model=GetXResponse1" in route
        assert "from ..models import GetXResponse, GetXResponse1, User" in route
        assert "APIRoute[" not in route

    def test_response_with_only_error_status_codes_generates_models(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证仅有 4xx/5xx JSON 响应（无 200/201）时仍生成 ``models.py`` 与对应 route import。

        行为契约：

        - spec 仅声明 ``400`` + ``500`` 两种 JSON 响应、没有 ``200``/``201`` 成功
          响应，且 ``components.schemas`` 故意为空（只有 ``$ref`` 指向的占位
          名）——目的是把模型生成的唯一开关留给 ``parser.has_json_payloads``,
          而不是 ``components.schemas`` 兜底分支。
        - ``parser.has_json_payloads`` 必须为 ``True``（与 renderer 对所有 JSON status
          一视同仁保持一致），CLI 必须生成 ``models.py``，并由 route 文件引用
          两个错误模型。
        - 这是 ``src/openapi/parser.py:get_endpoints`` 中 ``has_json_payloads`` 过滤器
          从 ``{"200", "201"}`` 改为"全部 status"后的一致性回归锁。
        - 防御：若 ``has_json_payloads`` 过滤器未更新，CLI 会跳过 ``models.py``
          生成，但 route 仍生成 ``from .models import Error, ServerError`` ——导入
          指向不存在的文件，运行时 ``ImportError``。本测试在生成阶段就拦截
          这种「silent missing import」漂移。

        设计说明：

        - ``$ref`` 指向 ``#/components/schemas/Error`` 等是 *dangling ref*;
          openapi-pydantic 加载期不验证，datamodel-code-generator 会发出
          ``DanglingRefWarning`` 并生成 ``class Error(RootModel[Any])`` 占位,
          满足断言 ``class Error in models`` / ``class ServerError in models``。
        - 这样 spec 仍然合法、可加载，但 ``components.schemas`` 是空 dict,
          ``schemas = {} or has_json_payloads`` 中只有 ``has_json_payloads=True`` 才能
          让 CLI 生成 ``models.py``。
        """
        spec = """\
openapi: 3.1.0
info:
  title: Error-Only Response API
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
        "400":
          description: bad request
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'
        "500":
          description: server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ServerError'
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        # ``has_json_payloads`` 为 True 时 CLI 必须生成 ``models.py``,包含两个错误类。
        assert (out_dir / "models.py").exists(), (
            "models.py 未生成 ——parser.has_json_payloads 在仅有错误响应时仍为 False,CLI 跳过了 generate_models 调用"
        )
        models = (out_dir / "models.py").read_text(encoding="utf-8")
        assert "class Error" in models
        assert "class ServerError" in models
        route = (out_dir / "endpoints" / "get_user.py").read_text(encoding="utf-8")
        assert "on_400: ClassVar[JSONResponseSpec]" in route
        assert "on_500: ClassVar[JSONResponseSpec]" in route
        assert "model=Error" in route
        assert "model=ServerError" in route
        assert "from ..models import Error, ServerError" in route
        assert "APIRoute[" not in route

    def test_parser_has_json_payloads_true_when_only_error_responses(self, cli_runner: Any, tmp_path: Path) -> None:
        """直接走 parser 探测 ``has_json_payloads``，验证错误响应纳入判定。

        行为契约：

        - 与 ``test_response_with_only_error_status_codes_generates_models``
          互补，直接走 ``make_openapi_parser`` 验证 ``parser.has_json_payloads``
          属性值，避免 CLI 副作用掩盖判定错误。
        - 这是 MUST DO 中的「Probe misleading-success-output」步骤。
        """
        spec = """\
openapi: 3.1.0
info:
  title: Error-Only Parser Probe
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
        "400":
          description: bad request
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'
        "500":
          description: server error
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ServerError'
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")

        parser = make_openapi_parser(spec_file)
        parser.load()
        # ``get_endpoints()`` 必须先调,``has_json_payloads`` 由它内部计算。
        parser.get_endpoints()
        assert parser.has_json_payloads is True, "parser.has_json_payloads 应为 True ——4xx/5xx JSON 响应必须纳入判定"


# ============================================================
# Field Docstring Integration
# ============================================================


class TestBodyFieldDocstring:
    """Body 字段（urlencoded form / multipart form / scalar body / binary body）字段 docstring 端到端渲染测试。

    4 类 body 字段 × 4 种 docstring 形态：

    1. 仅有 description（单行三引号格式）
    2. description + 1 example（多行三引号，含 ``Example: <repr>``）
    3. description + 多个 examples（多行三引号 + 项目符号列表）
    4. 既无 description 也无 example（不渲染 docstring 行）

    验证 docstring 文本存在（不要求完全匹配字符串，避免过度耦合）。
    """

    @staticmethod
    def _build_spec(media_type: str, schema_block: str, components_block: str = "") -> str:
        """构造带 requestBody 的 OpenAPI 3.1 模板。

        :param schema_block: 完整的 schema body（不含 ``schema:`` 前缀）。
        """
        return f"""\
openapi: 3.1.0
info:
  title: Body Docstring API
  version: "1.0.0"
paths:
  /resource:
    post:
      operationId: postResource
      summary: 测试
      requestBody:
        required: true
        content:
          {media_type}:
            schema:
{schema_block}
      responses:
        "200":
          description: ok
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: string
{components_block}
"""

    @classmethod
    def _object_form_schema(cls, fields_block: str) -> str:
        """构造 ``type: object`` 表单 schema（含 properties 缩进）。"""
        return f"              type: object\n              properties:\n{fields_block}"

    @staticmethod
    def _run(cli_runner: Any, spec: str, out_dir: Path) -> str:
        """运行 CLI 并返回 route 文件内容。"""
        out_dir.mkdir(parents=True, exist_ok=True)
        spec_file = out_dir / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir), "--no-format"])
        assert result.exit_code == 0, result.output
        return (out_dir / "endpoints" / "post_resource.py").read_text(encoding="utf-8")

    @pytest.mark.parametrize(
        ("media_type", "fields_block", "field_token", "docstring_token"),
        [
            (
                "application/x-www-form-urlencoded",
                '                username:\n                  type: string\n                  description: "用户名"\n',
                "username: Annotated[str, Form()]",
                '"""用户名"""',
            ),
            (
                "multipart/form-data",
                "                avatar:\n"
                "                  type: string\n"
                "                  format: binary\n"
                '                  description: "头像文件"\n',
                "avatar: UploadFile",
                '"""头像文件"""',
            ),
        ],
    )
    def test_form_field_description_only_renders_single_line(
        self,
        cli_runner: Any,
        tmp_path: Path,
        media_type: str,
        fields_block: str,
        field_token: str,
        docstring_token: str,
    ) -> None:
        """form 字段（urlencoded 标量 + multipart file）仅有 description 时渲染单行 docstring。"""
        spec = self._build_spec(media_type=media_type, schema_block=self._object_form_schema(fields_block))
        content = self._run(cli_runner, spec, tmp_path / "out")
        assert field_token in content, content
        assert docstring_token in content, content

    @pytest.mark.parametrize(
        ("media_type", "fields_block", "field_token", "description_token", "example_token"),
        [
            (
                "application/x-www-form-urlencoded",
                "                username:\n"
                "                  type: string\n"
                '                  description: "用户名"\n'
                "                  example: alice\n",
                "username: Annotated[str, Form()]",
                "用户名",
                "Example: 'alice'",
            ),
            (
                "multipart/form-data",
                "                avatar:\n"
                "                  type: string\n"
                "                  format: binary\n"
                '                  description: "头像文件"\n'
                "                  example: <binary>\n",
                "avatar: UploadFile",
                "头像文件",
                "Example: '<binary>'",
            ),
        ],
    )
    def test_form_field_description_and_single_example_renders_multiline(
        self,
        cli_runner: Any,
        tmp_path: Path,
        media_type: str,
        fields_block: str,
        field_token: str,
        description_token: str,
        example_token: str,
    ) -> None:
        """form 字段含 description + 1 example 时，docstring 是多行 + ``Example: <repr>``。"""
        spec = self._build_spec(media_type=media_type, schema_block=self._object_form_schema(fields_block))
        content = self._run(cli_runner, spec, tmp_path / "out")
        assert field_token in content
        assert description_token in content
        assert example_token in content

    @pytest.mark.parametrize(
        ("media_type", "fields_block", "field_token", "description_token"),
        [
            (
                "application/x-www-form-urlencoded",
                "                username:\n"
                "                  type: string\n"
                '                  description: "用户名"\n'
                "                  examples:\n"
                "                    - alice\n"
                "                    - bob\n"
                "                    - carol\n",
                "username: Annotated[str, Form()]",
                "用户名",
            ),
            (
                "multipart/form-data",
                "                avatar:\n"
                "                  type: string\n"
                "                  format: binary\n"
                '                  description: "头像文件"\n'
                "                  examples:\n"
                "                    - <jpeg>\n"
                "                    - <png>\n",
                "avatar: UploadFile",
                "头像文件",
            ),
        ],
    )
    def test_form_field_description_and_multiple_examples_renders_bullets(
        self,
        cli_runner: Any,
        tmp_path: Path,
        media_type: str,
        fields_block: str,
        field_token: str,
        description_token: str,
    ) -> None:
        """form 字段含 description + 多个 examples 时，docstring 是多行 + 项目符号列表。"""
        spec = self._build_spec(media_type=media_type, schema_block=self._object_form_schema(fields_block))
        content = self._run(cli_runner, spec, tmp_path / "out")
        assert field_token in content
        assert description_token in content
        assert "Examples:" in content

    @pytest.mark.parametrize(
        ("media_type", "fields_block", "field_token"),
        [
            (
                "application/x-www-form-urlencoded",
                "                username:\n                  type: string\n",
                "username: Annotated[str, Form()]",
            ),
            (
                "multipart/form-data",
                "                avatar:\n                  type: string\n                  format: binary\n",
                "avatar: UploadFile",
            ),
        ],
    )
    def test_form_field_no_description_no_example_no_docstring(
        self,
        cli_runner: Any,
        tmp_path: Path,
        media_type: str,
        fields_block: str,
        field_token: str,
    ) -> None:
        """form 字段既无 description 也无 example 时，docstring 为 None，模板条件跳过。"""
        spec = self._build_spec(media_type=media_type, schema_block=self._object_form_schema(fields_block))
        content = self._run(cli_runner, spec, tmp_path / "out")
        assert field_token in content
        compile(content, "post_resource.py", "exec")

    def test_scalar_body_description_only_renders_single_line(self, cli_runner: Any, tmp_path: Path) -> None:
        """scalar JSON integer body 仅有 description 时渲染单行 docstring。"""
        spec = self._build_spec(
            media_type="application/json",
            schema_block='              type: integer\n              description: "分数"\n',
        )
        content = self._run(cli_runner, spec, tmp_path / "out")
        assert "body: Annotated[int, Body(media_type='application/json')]" in content
        assert '"""分数"""' in content

    def test_scalar_body_description_and_single_example_renders_multiline(
        self, cli_runner: Any, tmp_path: Path
    ) -> None:
        """scalar body 含 description + 1 example 时，docstring 多行 + ``Example: <repr>``。"""
        spec = self._build_spec(
            media_type="application/json",
            schema_block='              type: integer\n              description: "分数"\n              example: 100\n',
        )
        content = self._run(cli_runner, spec, tmp_path / "out")
        assert "body: Annotated[int, Body(media_type='application/json')]" in content
        assert "分数" in content
        assert "Example: 100" in content

    def test_scalar_body_description_and_multiple_examples_renders_bullets(
        self, cli_runner: Any, tmp_path: Path
    ) -> None:
        """scalar body 含 description + 多 examples 时，docstring 多行 + 项目符号列表。"""
        spec = self._build_spec(
            media_type="application/json",
            schema_block=(
                "              type: integer\n"
                '              description: "分数"\n'
                "              examples:\n"
                "                - 100\n"
                "                - 200\n"
                "                - 300\n"
            ),
        )
        content = self._run(cli_runner, spec, tmp_path / "out")
        assert "body: Annotated[int, Body(media_type='application/json')]" in content
        assert "分数" in content
        assert "Examples:" in content
        assert "- 100" in content
        assert "- 200" in content
        assert "- 300" in content

    def test_scalar_body_no_description_no_example_no_docstring(self, cli_runner: Any, tmp_path: Path) -> None:
        """scalar body 既无 description 也无 example 时，docstring 为 None，模板条件跳过。"""
        spec = self._build_spec(
            media_type="application/json",
            schema_block="              type: integer\n",
        )
        content = self._run(cli_runner, spec, tmp_path / "out")
        assert "body: Annotated[int, Body(media_type='application/json')]" in content
        compile(content, "post_resource.py", "exec")

    def test_binary_body_no_description_no_example_no_docstring(self, cli_runner: Any, tmp_path: Path) -> None:
        """binary body schema 固定为 ``string + format=binary``，通常无 description/example。

        spec 中即使声明 description 也会经 builder 处理，验证 docstring 仍走
        ``build_upload_file_field_line`` 路径——空 docstring 时模板不插空行。
        """
        spec_yaml = """\
openapi: 3.1.0
info:
  title: Binary API
  version: "1.0.0"
paths:
  /upload:
    post:
      operationId: uploadFile
      summary: 上传
      requestBody:
        required: true
        content:
          application/octet-stream:
            schema:
              type: string
              format: binary
      responses:
        "200":
          description: ok
"""
        out_dir = tmp_path / "out"
        out_dir.mkdir(parents=True, exist_ok=True)
        spec_file = out_dir / "spec.yaml"
        spec_file.write_text(spec_yaml, encoding="utf-8")
        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir), "--no-format"])
        assert result.exit_code == 0, result.output
        content = (out_dir / "endpoints" / "upload_file.py").read_text(encoding="utf-8")
        assert "body: UploadFile" in content
        assert "upload_as_multipart=False" in content
        compile(content, "upload_file.py", "exec")


# ============================================================
# Endpoint Docstring — summary is None
# ============================================================


class TestClassDocstringWithoutSummary:
    """端点 summary=None（OpenAPI spec 中未声明 summary 字段）时的 class docstring 回归测试。

    根因：Jinja2 ``default`` filter 只对 **undefined** 变量生效，不对 ``None`` 生效。
    当 spec 里 endpoint 没有 ``summary`` 字段时，parser 把 summary 设为 ``None``，
    Jinja2 的 ``{{ summary | default(operation_id) }}`` 把 ``None`` 字面渲染成字符串，
    再拼上 ``。`` 变成字面量 ``None`` 加句号。

    修复：``{{ summary or operation_id }}`` 在 Jinja2 中是标准 idiom，
    当 summary 为 ``None``（或任何 falsy 值）时回退到 operation_id。

    覆盖三种情况：

    1. summary=None → class docstring 不含 ``None`` 字面量
    2. summary="实际摘要" → class docstring 含实际摘要文本
    3. summary=None + description="实际描述" → 描述在多行 docstring 中正常显示
    """

    @staticmethod
    def _build_spec(
        path: str,
        method: str,
        operation_id: str,
        summary: str | None,
        description: str | None = None,
    ) -> str:
        """构造一个 OpenAPI 3.1 规范，summary / description 可为 None。"""
        summary_line = f"      summary: {summary}" if summary else ""
        description_line = f"      description: {description}" if description else ""
        return f"""\
openapi: 3.1.0
info:
  title: Docstring API
  version: "1.0.0"
paths:
  {path}:
    {method}:
      operationId: {operation_id}
{summary_line}
{description_line}
      responses:
        "200":
          description: ok
"""

    @staticmethod
    def _run(cli_runner: Any, spec: str, out_dir: Path) -> str:
        """运行 CLI 并返回 route 文件内容。"""
        out_dir.mkdir(parents=True, exist_ok=True)
        spec_file = out_dir / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir), "--no-format"])
        assert result.exit_code == 0, result.output
        return (out_dir / "endpoints" / "get_resource.py").read_text(encoding="utf-8")

    def test_summary_none_no_literal_none_in_docstring(self, cli_runner: Any, tmp_path: Path) -> None:
        """summary=None 时，class docstring 不含 ``None`` 字面量（回退到 operation_id）。

        场景：OpenAPI spec 中 endpoint 未声明 summary 字段，
        parser.summary 收到 None，模板渲染 ``getResource`` 而不是 ``None``。
        """
        spec = self._build_spec(
            path="/resource",
            method="get",
            operation_id="getResource",
            summary=None,
        )
        content = self._run(cli_runner, spec, tmp_path / "out")
        # module docstring（第 1 行）不应出现 "None" 字面量
        assert '"""None' not in content, "模块 docstring 不应出现 None 字面量"
        # class docstring（第 25 行附近）也不应出现 "None" 字面量
        # 1a42663 之后：summary/description 都为空时不渲染 docstring，operation_id 仅出现在 class 名。
        assert "class GetResource(APIRoute):" in content
        compile(content, "get_resource.py", "exec")

    def test_summary_provided_uses_summary_text(self, cli_runner: Any, tmp_path: Path) -> None:
        """summary 有值时，class docstring 使用该值而不是 operation_id。"""
        spec = self._build_spec(
            path="/resource",
            method="get",
            operation_id="getResource",
            summary="获取资源详情",
        )
        content = self._run(cli_runner, spec, tmp_path / "out")
        assert "获取资源详情" in content, "summary 有值时应使用 summary 文本"
        assert '"""None' not in content, "summary 有值时也不应出现 None 字面量"
        compile(content, "get_resource.py", "exec")

    def test_summary_none_with_description_renders_multiline_docstring(
        self, cli_runner: Any, tmp_path: Path
    ) -> None:
        """summary=None 但有 description 时，多行 docstring 正确显示 description 内容。

        验证 description 不被 summary=None 的字面量污染。
        """
        spec = self._build_spec(
            path="/resource",
            method="get",
            operation_id="getResource",
            summary=None,
            description="这是资源描述",
        )
        content = self._run(cli_runner, spec, tmp_path / "out")
        # description 文本应该出现
        assert "这是资源描述" in content, "description 有值时应出现在 docstring 中"
        # 不应有 None 字面量
        assert '"""None' not in content, "summary=None 时不应出现 None 字面量"
        compile(content, "get_resource.py", "exec")


# ============================================================
# Import Ordering and Unused Import Regression
# ============================================================


class TestImportOrderingAndNoUnused:
    """import 顺序与 unused import 回归测试。

    修复根因：

    1. 模板条件过宽：``import_model`` 不应触发 ``Annotated`` 或 ``Body`` import。
       - ``body: ModelName`` 形式不需要 ``Annotated``（无 ``Annotated[...]`` 包装）
       - ``body: ModelName`` 形式不需要 ``Body(...)``（FastAPI 直接用类名）
       - ``Annotated`` 只在 param/header/scalar/form 场景需要（``Annotated[T, ...]``）
       - ``Body`` 只在 scalar body 场景需要（``Body(media_type=...)``）

    2. ``{% if imported_models %}`` 块在 ``from stoma import ...`` 之前，
       违反 isort 默认顺序（__future__ → stdlib → third-party → first-party → local）。

    3. ``render_to_file`` 的 ruff 命令缺 F401，无法自动清 unused imports。

    覆盖三种场景：

    1. JSON body only（仅 ``import_model``，无 param/header/form/scalar）
       → 无 ``Annotated`` import + 无 ``Body`` import + ``.models`` 在 ``stoma`` 之后
    2. JSON body + query param
       → ``Annotated`` import 存在且被使用
    3. form body
       → ``Form`` import + ``Annotated`` import 都存在
    """

    @staticmethod
    def _build_spec_with_json_body(path: str, method: str, operation_id: str, add_query_param: bool = False) -> str:
        """构造仅含 JSON body（``$ref`` 模型引用）的 OpenAPI 3.1 规范。"""
        query_block = """\
      parameters:
        - name: filterBy
          in: query
          schema:
            type: string
""" if add_query_param else ""

        return f"""\
openapi: 3.1.0
info:
  title: Import Order API
  version: "1.0.0"
paths:
  {path}:
    {method}:
      operationId: {operation_id}
      summary: 测试
{query_block}      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/Item'
      responses:
        "200":
          description: ok
components:
  schemas:
    Item:
      type: object
      required: [name]
      properties:
        name:
          type: string
"""

    @staticmethod
    def _build_spec_with_form_body(path: str, method: str, operation_id: str) -> str:
        """构造 form body（``application/x-www-form-urlencoded``）的 OpenAPI 3.1 规范。"""
        return f"""\
openapi: 3.1.0
info:
  title: Form Body API
  version: "1.0.0"
paths:
  {path}:
    {method}:
      operationId: {operation_id}
      summary: 测试表单
      requestBody:
        required: true
        content:
          application/x-www-form-urlencoded:
            schema:
              type: object
              required: [name]
              properties:
                name:
                  type: string
                quantity:
                  type: integer
      responses:
        "200":
          description: ok
"""

    @staticmethod
    def _run(cli_runner: Any, spec: str, out_dir: Path, file_name: str) -> str:
        """运行 CLI 并返回 route 文件内容。"""
        out_dir.mkdir(parents=True, exist_ok=True)
        spec_file = out_dir / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir), "--no-format"])
        assert result.exit_code == 0, result.output
        return (out_dir / "endpoints" / file_name).read_text(encoding="utf-8")

    def test_json_body_only_no_unused_imports(self, cli_runner: Any, tmp_path: Path) -> None:
        """JSON body only（仅 ``import_model``）→ 无 ``Annotated`` import + 无 ``Body`` import + 正确顺序。

        当 endpoint 只有 JSON body（``$ref`` 引用模型），没有 param/header/form/scalar 时：
        - 不应导入 ``Annotated``（没有 ``Annotated[...]`` 包装的字段）
        - 不应导入 ``Body``（``body: ModelName`` 直接用类名，不需要 ``Body(...)``）
        - ``from .models import ...`` 必须在 ``from stoma import ...`` 之后（isort 默认顺序）
        """
        spec = self._build_spec_with_json_body("/items", "post", "createItem")
        content = self._run(cli_runner, spec, tmp_path / "out", "create_item.py")

        # 验证 import_model 被正确导入
        assert "from ..models import Item" in content
        # 验证 body 使用模型名形式
        assert "body: Item" in content

        # JSON body only → 不应有 Annotated import
        assert "from typing import Annotated" not in content, "JSON body only 不应导入 Annotated"

        # JSON body only → 不应有 Body import（body: ModelName 不需要 Body(...)）
        # 注意：这里不能简单检查 "Body" 不在 content 中，因为可能是 "APIRoute" 的一部分
        # 所以检查 "Body" 作为独立 import 存在（后面是逗号、空格、换行等）
        import_stoma_line = [line for line in content.split("\n") if "from stoma import" in line]
        if import_stoma_line:
            assert "Body" not in import_stoma_line[0], "JSON body only 不应导入 Body"

        # 验证 import 顺序：.models 必须在 stoma 之后
        models_pos = content.index("from ..models import")
        stoma_pos = content.index("from stoma import")
        assert models_pos > stoma_pos, ".models 必须在 stoma 之后（isort 默认顺序）"

        # 确保代码可编译
        compile(content, "create_item.py", "exec")

    def test_json_body_with_query_param_has_annotated(self, cli_runner: Any, tmp_path: Path) -> None:
        """JSON body + query param → ``Annotated`` import 存在且被使用。

        当 endpoint 有 query param 时，param 字段使用 ``Annotated[T, ...]`` 包装，
        因此必须导入 ``Annotated``。
        """
        spec = self._build_spec_with_json_body("/items", "post", "createItem", add_query_param=True)
        content = self._run(cli_runner, spec, tmp_path / "out", "create_item.py")

        # 验证 Annotated 被导入
        assert "from typing import Annotated" in content, "有 query param 时应导入 Annotated"
        # 验证 Annotated 被使用（query param 使用 Annotated）
        assert "Annotated[" in content, "query param 应使用 Annotated[...]"

        # JSON body 仍不应导入 Body
        import_stoma_line = [line for line in content.split("\n") if "from stoma import" in line]
        if import_stoma_line:
            assert "Body" not in import_stoma_line[0], "有 query param 的 JSON body 不应导入 Body"

        compile(content, "create_item.py", "exec")

    def test_form_body_has_form_and_annotated(self, cli_runner: Any, tmp_path: Path) -> None:
        """form body → ``Form`` import + ``Annotated`` import 都存在。

        form 字段使用 ``Annotated[T, Form(...)]`` 包装，因此必须导入
        ``Annotated`` 和 ``Form``。
        """
        spec = self._build_spec_with_form_body("/items", "post", "createItem")
        content = self._run(cli_runner, spec, tmp_path / "out", "create_item.py")

        # 验证 Form 被导入
        assert "from stoma import" in content
        import_stoma_line = [line for line in content.split("\n") if "from stoma import" in line]
        assert any("Form" in line for line in import_stoma_line), "form body 应导入 Form"

        # 验证 Annotated 被导入（Form 使用 Annotated[...] 包装）
        assert "from typing import Annotated" in content, "form body 应导入 Annotated"

        # 验证 Annotated 和 Form 被使用
        assert "Annotated[" in content, "form 字段应使用 Annotated[...]"
        assert "Form()" in content, "form 字段应使用 Form()"

        compile(content, "create_item.py", "exec")


# ============================================================
# Endpoint Docstring — summary/description Conditional Rendering
# ============================================================


class TestEndpointDocstring:
    """Endpoint 模块 docstring 和类 docstring 的条件渲染回归测试。

    验证 `build_endpoint_docstring` + `endpoint.py.jinja2` 模板的条件渲染逻辑：

    - summary + description 都有 → 两者都渲染
    - 仅 summary → 单行 docstring
    - 仅 description → description 内容（单行，ruff 格式化后）
    - 都没有 → 不渲染 docstring（模块和类），operation_id 字面量不出现
    """

    @staticmethod
    def _build_spec(
        path: str,
        method: str,
        operation_id: str,
        summary: str | None,
        description: str | None = None,
    ) -> str:
        """构造一个 OpenAPI 3.1 规范，summary / description 可为 None。"""
        summary_line = f"      summary: {summary}" if summary else "      summary:"
        description_line = f"      description: {description}" if description else ""
        return f"""\
openapi: 3.1.0
info:
  title: Docstring API
  version: "1.0.0"
paths:
  {path}:
    {method}:
      operationId: {operation_id}
{summary_line}
{description_line}
      responses:
        "200":
          description: ok
"""

    @staticmethod
    def _run(cli_runner: Any, spec: str, out_dir: Path) -> str:
        """运行 CLI 并返回 route 文件内容。"""
        out_dir.mkdir(parents=True, exist_ok=True)
        spec_file = out_dir / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir), "--no-format"])
        assert result.exit_code == 0, result.output
        return (out_dir / "endpoints" / "get_resource.py").read_text(encoding="utf-8")

    def test_summary_only_renders_single_line_docstring(self, cli_runner: Any, tmp_path: Path) -> None:
        """仅有 summary 时，模块 docstring 和类 docstring 都是单行。"""
        spec = self._build_spec(
            path="/resource",
            method="get",
            operation_id="getResource",
            summary="获取资源",
            description=None,
        )
        content = self._run(cli_runner, spec, tmp_path / "out")
        # 单行 docstring，含 summary 文本 + 中文句号
        assert '"""获取资源。"""' in content, "summary-only 应生成单行 docstring"
        # 不应出现 None 字面量或 operation_id 字面量
        assert '"""None' not in content
        assert '"""getResource' not in content
        compile(content, "get_resource.py", "exec")

    def test_description_only_renders_multiline_docstring(self, cli_runner: Any, tmp_path: Path) -> None:
        """仅有 description 时，docstring 只含 description 内容（无 summary）。"""
        spec = self._build_spec(
            path="/resource",
            method="get",
            operation_id="getResource",
            summary=None,
            description="这是资源描述",
        )
        content = self._run(cli_runner, spec, tmp_path / "out")
        # description 出现在 docstring 中
        assert "这是资源描述" in content, "description-only 应生成含 description 的 docstring"
        # operation_id 不应出现在 docstring 中
        assert '"""getResource' not in content, "description-only 时 operation_id 不应出现在 docstring"
        compile(content, "get_resource.py", "exec")

    def test_summary_and_description_renders_both(self, cli_runner: Any, tmp_path: Path) -> None:
        """summary 和 description 都有时，两者都渲染到 docstring 中。"""
        spec = self._build_spec(
            path="/resource",
            method="get",
            operation_id="getResource",
            summary="获取资源",
            description="获取指定资源的完整信息。",
        )
        content = self._run(cli_runner, spec, tmp_path / "out")
        # 两者都出现
        assert "获取资源" in content, "summary 应出现"
        assert "获取指定资源的完整信息。" in content, "description 应出现"
        # 模块 docstring 有 "Generated from OpenAPI: getResource"
        assert "Generated from OpenAPI: getResource" in content, "模块 docstring 应含 operation_id 标记"
        compile(content, "get_resource.py", "exec")

    def test_neither_summary_nor_description_omits_docstring(self, cli_runner: Any, tmp_path: Path) -> None:
        """summary 和 description 都没有时，模块 docstring 和类 docstring 都不渲染。

        这是核心回归测试：原来 summary or operation_id fallback 会生成
        "operationId。" 这样的纯 operation_id docstring，
        现在应该完全不出现 docstring。
        """
        spec = self._build_spec(
            path="/resource",
            method="get",
            operation_id="getResource",
            summary=None,
            description=None,
        )
        content = self._run(cli_runner, spec, tmp_path / "out")
        # operation_id 不应出现在任何 docstring 中
        assert '"""getResource' not in content, "无 summary/description 时 operation_id 不应出现在 docstring"
        # 模块 docstring 不存在（文件以 from __future__ 开头）
        first_line = content.split("\n")[0]
        assert first_line.startswith("from __future__"), "无 docstring 时文件第一行应是 import"
        compile(content, "get_resource.py", "exec")


@dataclass
class _FakeMediaType:
    """测试夹具：OpenAPI MediaType 对象的最小化替身，仅暴露 ``media_type_schema``。"""

    media_type_schema: Any = None


class _FakeResponse(BaseModel):
    """测试夹具：OpenAPI Response 对象的最小化 BaseModel。

    ``content`` 字段使用 ``arbitrary_types_allowed`` 以接受 ``_FakeMediaType`` 实例
    作为值——``_extract_response_specs`` 只用 ``getattr(..., "media_type_schema", None)``
    读取 schema，不需要真实的 openapi-pydantic 模型。
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    description: str | None = None
    content: dict[str, _FakeMediaType] = {}


def _make_ref(name: str) -> Reference31:
    """构造一个 ``Reference31`` 实例，ref 指向 ``#/components/schemas/<name>``。"""
    return Reference31(ref=f"#/components/schemas/{name}")


def _make_endpoint(
    responses: dict[str, _FakeResponse] | None,
    operation_id: str = "getUser",
) -> Endpoint[Any, Any, _FakeResponse]:
    """构造仅含 ``operation_id`` + ``responses`` 字段的最小 :class:`Endpoint`。

    :param responses: responses 字典，None 表示无响应。
    :param operation_id: 派生 ``Class name`` 与 inline 模型名前缀。
    :return: 可直接传给 :meth:`EndpointRenderer._extract_response_specs` 的 Endpoint。
    """
    return Endpoint[Any, Any, _FakeResponse](
        operation_id=operation_id,
        method="GET",
        path="/test",
        summary=None,
        description=None,
        parameters=[],
        request_body=None,
        responses=responses,
        spec_version="3.1",
    )


class _DuplicateItemResponses(dict):
    """测试夹具：dict 子类，``items()`` 重复 yield 两次。

    模拟罕见但理论上可能的「同 ``(status, media_type)`` 多次出现」场景——
    规范 ``dict`` 自身不允许 key 重复，但允许 dict 子类返回重复 items；
    :meth:`EndpointRenderer._extract_response_specs` 的去重逻辑应在此场景下触发
    :attr:`GenerationErrorKind.DUPLICATE_RESPONSE_SPEC` 警告。
    """

    def items(self) -> Any:
        for key in list(dict.keys(self)):
            yield key, dict.__getitem__(self, key)
        for key in list(dict.keys(self)):
            yield key, dict.__getitem__(self, key)


class TestExtractResponseSpecs:
    """验证 :meth:`EndpointRenderer._extract_response_specs` 的逐 status + 逐 media_type 提取行为。"""

    def test_extract_single_media(self) -> None:
        """200 + 单 JSON media → 1 条 decl，attr_name=``on_200``。

        基准场景：单 status、单 media type、最常见的 happy path。
        """
        renderer = make_endpoint_renderer("3.1")
        endpoint = _make_endpoint(
            {
                "200": _FakeResponse(
                    content={"application/json": _FakeMediaType(media_type_schema=_make_ref("User"))},
                ),
            },
        )
        decls = renderer._extract_response_specs(endpoint.responses, endpoint)
        assert len(decls) == 1
        decl = decls[0]
        assert decl == ResponseSpecDecl(
            attr_name="on_200",
            status_code=200,
            status_matcher=200,
            media_type="application/json",
            model_name="User",
            is_json=True,
            spec_class="JSONResponseSpec",
            status_code_or_matcher="status_code=200",
        )
        assert renderer.errors == []

    def test_extract_multi_media(self) -> None:
        """200 + JSON + text/xml → 2 条 decl，attrs 按 sanitize 后的 media_type 消歧。

        验证多 media type 时 attr_name 必须加后缀消歧——避免两个 decl
        都用 ``on_200`` 引发「duplicate attribute」语法错误。
        """
        renderer = make_endpoint_renderer("3.1")
        endpoint = _make_endpoint(
            {
                "200": _FakeResponse(
                    content={
                        "application/json": _FakeMediaType(media_type_schema=_make_ref("User")),
                        "text/xml": _FakeMediaType(media_type_schema=None),
                    },
                ),
            },
        )
        decls = renderer._extract_response_specs(endpoint.responses, endpoint)
        assert len(decls) == 2
        assert decls[0] == ResponseSpecDecl(
            attr_name="on_200_application_json",
            status_code=200,
            status_matcher=200,
            media_type="application/json",
            model_name="User",
            is_json=True,
            spec_class="JSONResponseSpec",
            status_code_or_matcher="status_code=200",
        )
        assert decls[1] == ResponseSpecDecl(
            attr_name="on_200_text_xml",
            status_code=200,
            status_matcher=200,
            media_type="text/xml",
            model_name=None,
            is_json=False,
            spec_class="RawResponseSpec",
            status_code_or_matcher="status_code=200",
        )
        assert renderer.errors == []

    def test_extract_default(self) -> None:
        """``default`` 响应 → 1 条 decl，attr_name=``on_default``、matcher 接受所有 status。

        验证 OpenAPI ``default`` 通配符被转换为 ``lambda s: True`` 谓词，
        attr_name 不含数字而是字面 ``on_default``。
        """
        renderer = make_endpoint_renderer("3.1")
        endpoint = _make_endpoint(
            {
                "default": _FakeResponse(
                    content={"application/json": _FakeMediaType(media_type_schema=_make_ref("Error"))},
                ),
            },
        )
        decls = renderer._extract_response_specs(endpoint.responses, endpoint)
        assert len(decls) == 1
        decl = decls[0]
        assert decl.attr_name == "on_default"
        assert decl.status_code == "default"
        assert decl.status_matcher(200)
        assert decl.status_matcher(404)
        assert decl.status_matcher(500)
        assert decl.media_type == "application/json"
        assert decl.model_name == "Error"
        assert decl.is_json is True

    def test_extract_4xx_wildcard(self) -> None:
        """``4XX`` 通配符 → 1 条 decl，attr_name=``on_4xx``、matcher 覆盖 ``400 <= s < 500``。

        验证 OpenAPI 范围通配符被转换为 :func:`make_range_matcher` 生成的谓词。
        attr_name 全小写 ``on_4xx``，status_code 保留原始大写 ``"4XX"`` 字符串。
        """
        renderer = make_endpoint_renderer("3.1")
        endpoint = _make_endpoint(
            {
                "4XX": _FakeResponse(
                    content={"application/json": _FakeMediaType(media_type_schema=_make_ref("Error"))},
                ),
            },
        )
        decls = renderer._extract_response_specs(endpoint.responses, endpoint)
        assert len(decls) == 1
        decl = decls[0]
        assert decl.attr_name == "on_4xx"
        assert decl.status_code == "4XX"
        assert decl.status_matcher(400)
        assert decl.status_matcher(404)
        assert decl.status_matcher(499)
        assert not decl.status_matcher(500)
        assert not decl.status_matcher(399)
        assert decl.is_json is True

    def test_extract_multi_json_media_types(self) -> None:
        """200 + ``application/json`` + ``application/problem+json`` → 2 条 decl。

        验证本 refactor 的核心修复——旧 :meth:`_get_json_response_types` 只取
        第一个 JSON media type，新方法必须遍历所有 JSON 家族 media type
        （含 RFC 6839 ``+json`` structured syntax suffix）。
        """
        renderer = make_endpoint_renderer("3.1")
        endpoint = _make_endpoint(
            {
                "200": _FakeResponse(
                    content={
                        "application/json": _FakeMediaType(media_type_schema=_make_ref("User")),
                        "application/problem+json": _FakeMediaType(media_type_schema=_make_ref("Problem")),
                    },
                ),
            },
        )
        decls = renderer._extract_response_specs(endpoint.responses, endpoint)
        assert len(decls) == 2
        assert decls[0] == ResponseSpecDecl(
            attr_name="on_200_application_json",
            status_code=200,
            status_matcher=200,
            media_type="application/json",
            model_name="User",
            is_json=True,
            spec_class="JSONResponseSpec",
            status_code_or_matcher="status_code=200",
        )
        assert decls[1] == ResponseSpecDecl(
            attr_name="on_200_application_problem_plus_json",
            status_code=200,
            status_matcher=200,
            media_type="application/problem+json",
            model_name="Problem",
            is_json=True,
            spec_class="JSONResponseSpec",
            status_code_or_matcher="status_code=200",
        )
        assert renderer.errors == []

    def test_extract_duplicate_skipped_with_warning(self) -> None:
        """``_DuplicateItemResponses`` 模拟重复 ``(status, media_type)`` → 第二次跳过 + DUPLICATE_RESPONSE_SPEC 警告。

        验证去重保护逻辑：使用 ``_DuplicateItemResponses``（dict 子类，
        ``items()`` 重复 yield）模拟罕见但需处理的「同 ``(status, media_type)``
        多次出现」场景，第二次出现应被跳过并 emit
        :attr:`GenerationErrorKind.DUPLICATE_RESPONSE_SPEC` 警告。

        直接把 ``_DuplicateItemResponses`` 实例传给 ``_extract_response_specs``
        而不绕道 ``Endpoint(...)``——Pydantic 验证会把 dict 子类 normalize 回
        普通 dict，子类的重复 ``items()`` 行为会丢失。
        """
        renderer = make_endpoint_renderer("3.1")
        endpoint = _make_endpoint(None)
        responses = _DuplicateItemResponses(
            {
                "200": _FakeResponse(
                    content={"application/json": _FakeMediaType(media_type_schema=_make_ref("User"))},
                ),
            },
        )
        decls = renderer._extract_response_specs(responses, endpoint)
        assert len(decls) == 1
        assert decls[0].attr_name == "on_200"
        assert decls[0].model_name == "User"
        duplicate_errors = [e for e in renderer.errors if e.kind == GenerationErrorKind.DUPLICATE_RESPONSE_SPEC]
        assert len(duplicate_errors) == 1
        assert "200" in duplicate_errors[0].message
        assert "application/json" in duplicate_errors[0].message
        assert duplicate_errors[0].location == "GET /test"

    def test_extract_returns_empty_when_responses_is_none(self) -> None:
        """``responses=None`` 时返回空列表——与旧 :meth:`_get_json_response_types` 行为一致。"""
        renderer = make_endpoint_renderer("3.1")
        endpoint = _make_endpoint(None)
        assert renderer._extract_response_specs(endpoint.responses, endpoint) == []
        assert renderer.errors == []

    def test_extract_returns_empty_when_content_is_empty(self) -> None:
        """responses 含但 ``content`` 为空 → 返回空列表（无 media type 可声明）。"""
        renderer = make_endpoint_renderer("3.1")
        endpoint = _make_endpoint({"200": _FakeResponse(content={})})
        assert renderer._extract_response_specs(endpoint.responses, endpoint) == []

    def test_make_range_matcher_inclusive_start_exclusive_end(self) -> None:
        """``make_range_matcher(start, end)`` 满足 ``start <= s < end`` 半开区间语义。

        与 Python ``range(start, end)`` 一致——含 start、不含 end。
        """
        m = make_range_matcher(400, 500)
        assert m(400)
        assert m(404)
        assert m(499)
        assert not m(500)
        assert not m(399)
        m5xx = make_range_matcher(500, 600)
        assert m5xx(500) and m5xx(599)
        assert not m5xx(499) and not m5xx(600)

    def test_parse_status_key_supports_all_wildcards(self) -> None:
        """``_parse_status_key`` 对 ``1XX`` / ``2XX`` / ``3XX`` / ``4XX`` / ``5XX`` 全覆盖。"""
        renderer = make_endpoint_renderer("3.1")
        for digit, base in [(1, 100), (2, 200), (3, 300), (4, 400), (5, 500)]:
            attr, code, matcher = renderer._parse_status_key(f"{digit}XX")
            assert attr == f"on_{digit}xx"
            assert code == f"{digit}XX"
            assert matcher(base)
            assert matcher(base + 99)
            assert not matcher(base - 1)
            assert not matcher(base + 100)

    def test_parse_status_key_default_uses_true_predicate(self) -> None:
        """``default`` 解析为 ``lambda s: True`` 谓词，所有 status 均匹配。"""
        renderer = make_endpoint_renderer("3.1")
        _attr, _code, matcher = renderer._parse_status_key("default")
        assert matcher(100) and matcher(404) and matcher(500) and matcher(999)


def _capture_render_kwargs(
    renderer: Any,
    endpoint: Endpoint[Any, Any, Any],
) -> dict[str, Any]:
    """执行 ``renderer.render(endpoint)`` 并捕获传给模板 ``render()`` 的 kwargs。

    模板在 Wave 6.3 阶段尚未消费新增的 ``response_spec_decls`` /
    ``imported_specs`` / ``uses_classvar_import`` 变量（Wave 6.4 才切换），
    本辅助函数通过 ``unittest.mock`` 替换 ``renderer.env.get_template`` 返回的
    ``Template.render`` 方法，记录所有 kwargs 后返回给调用方做断言。

    :param renderer: 已初始化的 ``EndpointRenderer`` 实例。
    :param endpoint: 待渲染的 :class:`Endpoint` IR。
    :return: ``Template.render(**kwargs)`` 调用时的 kwargs 字典。
    """
    captured: dict[str, Any] = {}

    class _StubTemplate:
        def render(self, **kwargs: Any) -> str:  # noqa: ANN401 - test stub mirrors Jinja2 API
            captured.update(kwargs)
            return ""

    def _fake_get_template(_name: str) -> _StubTemplate:
        return _StubTemplate()

    renderer.env.get_template = _fake_get_template  # type: ignore[method-assign]
    renderer.render(endpoint)
    return captured


class TestRenderPassesResponseSpecDecls:
    """验证 :meth:`EndpointRenderer.render` 把 ``response_spec_decls`` 等新模板变量透传给模板。

    本测试类不验证最终 route 文件（Wave 6.4 才完成模板切换），而是直接捕获
    ``render()`` 内部传给 ``Template.render(...)`` 的 kwargs，断言：
    ``response_spec_decls`` 是 :class:`ResponseSpecDecl` 列表、
    ``imported_specs`` 按 JSON/Raw 类型正确收集、
    ``uses_classvar_import`` 反映 decl 存在性。
    """

    def test_render_passes_response_spec_decls_to_template(self) -> None:
        """200 + 单 JSON media → 模板收到 1 条 ``ResponseSpecDecl``。"""
        renderer = make_endpoint_renderer("3.1")
        endpoint = _make_endpoint(
            {
                "200": _FakeResponse(
                    content={"application/json": _FakeMediaType(media_type_schema=_make_ref("User"))},
                ),
            },
        )
        kwargs = _capture_render_kwargs(renderer, endpoint)
        assert "response_spec_decls" in kwargs
        decls = kwargs["response_spec_decls"]
        assert len(decls) == 1
        assert decls[0] == ResponseSpecDecl(
            attr_name="on_200",
            status_code=200,
            status_matcher=200,
            media_type="application/json",
            model_name="User",
            is_json=True,
            spec_class="JSONResponseSpec",
            status_code_or_matcher="status_code=200",
        )

    def test_render_passes_imported_specs_json_only(self) -> None:
        """仅 JSON 响应 → ``imported_specs == ["JSONResponseSpec"]``，不含 ``RawResponseSpec``。"""
        renderer = make_endpoint_renderer("3.1")
        endpoint = _make_endpoint(
            {
                "200": _FakeResponse(
                    content={"application/json": _FakeMediaType(media_type_schema=_make_ref("User"))},
                ),
            },
        )
        kwargs = _capture_render_kwargs(renderer, endpoint)
        assert kwargs["imported_specs"] == ["JSONResponseSpec"]

    def test_render_passes_imported_specs_raw_only(self) -> None:
        """仅 Raw 响应（``image/png``，``model_name=None``） → ``imported_specs == ["RawResponseSpec"]``。"""
        renderer = make_endpoint_renderer("3.1")
        endpoint = _make_endpoint(
            {
                "200": _FakeResponse(
                    content={"image/png": _FakeMediaType(media_type_schema=None)},
                ),
            },
        )
        kwargs = _capture_render_kwargs(renderer, endpoint)
        assert kwargs["imported_specs"] == ["RawResponseSpec"]

    def test_render_passes_imported_specs_both_json_and_raw(self) -> None:
        """JSON + Raw 混合 → ``imported_specs == ["JSONResponseSpec", "RawResponseSpec"]``。

        验证 JSON → Raw 的固定顺序，且两端都存在时才会两个都添加。
        """
        renderer = make_endpoint_renderer("3.1")
        endpoint = _make_endpoint(
            {
                "200": _FakeResponse(
                    content={
                        "application/json": _FakeMediaType(media_type_schema=_make_ref("User")),
                        "image/png": _FakeMediaType(media_type_schema=None),
                    },
                ),
            },
        )
        kwargs = _capture_render_kwargs(renderer, endpoint)
        assert kwargs["imported_specs"] == ["JSONResponseSpec", "RawResponseSpec"]

    def test_render_uses_classvar_import_true_when_decls_exist(self) -> None:
        """任意 decl 存在 → ``uses_classvar_import == True``。"""
        renderer = make_endpoint_renderer("3.1")
        endpoint = _make_endpoint(
            {
                "200": _FakeResponse(
                    content={"application/json": _FakeMediaType(media_type_schema=_make_ref("User"))},
                ),
            },
        )
        kwargs = _capture_render_kwargs(renderer, endpoint)
        assert kwargs["uses_classvar_import"] is True

    def test_render_uses_classvar_import_false_when_no_responses(self) -> None:
        """``responses=None`` → 0 个 decl → ``uses_classvar_import == False``。"""
        renderer = make_endpoint_renderer("3.1")
        endpoint = _make_endpoint(None)
        kwargs = _capture_render_kwargs(renderer, endpoint)
        assert kwargs["response_spec_decls"] == []
        assert kwargs["imported_specs"] == []
        assert kwargs["uses_classvar_import"] is False

    def test_render_uses_classvar_import_false_when_only_description(self) -> None:
        """``responses`` 含但 ``content`` 为空 → 0 个 decl → ``uses_classvar_import == False``。"""
        renderer = make_endpoint_renderer("3.1")
        endpoint = _make_endpoint({"200": _FakeResponse(content={})})
        kwargs = _capture_render_kwargs(renderer, endpoint)
        assert kwargs["response_spec_decls"] == []
        assert kwargs["uses_classvar_import"] is False

    def test_render_imported_models_collected_from_decl_model_names(self) -> None:
        """多 decl → ``imported_models`` 从 ``decl.model_name`` 去重收集。

        验证：顺序按 decl 出现顺序（spec 中 status 顺序），重复 model 去重。
        """
        renderer = make_endpoint_renderer("3.1")
        endpoint = _make_endpoint(
            {
                "200": _FakeResponse(
                    content={"application/json": _FakeMediaType(media_type_schema=_make_ref("User"))},
                ),
                "404": _FakeResponse(
                    content={"application/json": _FakeMediaType(media_type_schema=_make_ref("Error"))},
                ),
                "default": _FakeResponse(
                    content={
                        "application/problem+json": _FakeMediaType(media_type_schema=_make_ref("User")),
                    },
                ),
            },
        )
        kwargs = _capture_render_kwargs(renderer, endpoint)
        # User 出现两次（200 + default），只保留一次，按 spec 顺序 User 在 Error 前。
        assert kwargs["imported_models"] == ["User", "Error"]

    def test_render_imported_models_excludes_raw_decl_none(self) -> None:
        """Raw decl ``model_name=None`` 不污染 ``imported_models``。

        验证：JSON 模型的 ``User`` 仍正确收集，Raw 响应（``image/png`` 无 schema）不被加入。
        """
        renderer = make_endpoint_renderer("3.1")
        endpoint = _make_endpoint(
            {
                "200": _FakeResponse(
                    content={
                        "application/json": _FakeMediaType(media_type_schema=_make_ref("User")),
                        "image/png": _FakeMediaType(media_type_schema=None),
                    },
                ),
            },
        )
        kwargs = _capture_render_kwargs(renderer, endpoint)
        # Raw decl 的 model_name=None 被跳过，只剩 JSON decl 的 "User"。
        assert kwargs["imported_models"] == ["User"]
        assert None not in kwargs["imported_models"]

    def test_render_response_type_kept_for_template_backward_compat(self) -> None:
        """``response_type``（Union 字符串）由 decls 的 ``model_name`` 派生，保留到 Wave 6.4。

        验证：现有模板仍消费 ``APIRoute[T]`` 泛型语法，所以 ``render()`` 仍计算
        ``response_type``；多 status + 重复 model 时按 spec 顺序去重。
        """
        renderer = make_endpoint_renderer("3.1")
        endpoint = _make_endpoint(
            {
                "200": _FakeResponse(
                    content={"application/json": _FakeMediaType(media_type_schema=_make_ref("User"))},
                ),
                "404": _FakeResponse(
                    content={"application/json": _FakeMediaType(media_type_schema=_make_ref("Error"))},
                ),
                "201": _FakeResponse(
                    content={"application/json": _FakeMediaType(media_type_schema=_make_ref("User"))},
                ),
            },
        )
        kwargs = _capture_render_kwargs(renderer, endpoint)
        # 三个 JSON decl，User 出现两次（200 + 201），去重后 "User | Error"（按首次出现顺序）。
        assert kwargs["response_type"] == "User | Error"

    def test_render_response_type_empty_when_no_json_decls(self) -> None:
        """无任何 decl → ``response_type == ""``（模板 ``{% if response_type %}`` 跳过）。"""
        renderer = make_endpoint_renderer("3.1")
        endpoint = _make_endpoint(None)
        kwargs = _capture_render_kwargs(renderer, endpoint)
        assert kwargs["response_type"] == ""


class TestTemplateEmitsClassVarDeclarations:
    """验证模板输出 ``on_<status>: ClassVar[<spec_class>] = <spec_class>(...)`` 形式。

    Wave 6.4 模板切换后，渲染结果应满足：

    - ``class <Name>(APIRoute):`` 不带 ``[T]`` 泛型参数。
    - ``on_<status>: ClassVar[JSONResponseSpec] = JSONResponseSpec(...)``（JSON 路径，含 ``model=...``）。
    - ``on_<status>: ClassVar[RawResponseSpec] = RawResponseSpec(...)``（Raw 路径，无 ``model=``）。
    - ``from typing import ClassVar`` 在 ``uses_classvar_import=True`` 时出现。
    - ``from stoma import JSONResponseSpec`` / ``RawResponseSpec`` 按 ``imported_specs`` 添加。
    - 全文不含 ``APIRoute[``（带方括号的泛型语法已被淘汰）。
    """

    def _make_endpoint_with_json_response(
        self,
        responses: dict[str, _FakeResponse] | None,
        operation_id: str = "getUser",
    ) -> Endpoint[Any, Any, _FakeResponse]:
        """构造带 responses 的最小 :class:`Endpoint`，仅供 renderer.render 调用。"""
        return Endpoint[Any, Any, _FakeResponse](
            operation_id=operation_id,
            method="GET",
            path="/test",
            summary=None,
            description=None,
            parameters=[],
            request_body=None,
            responses=responses,
            spec_version="3.1",
        )

    def test_class_line_has_no_generic(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证渲染后 ``class <Name>(APIRoute):`` 无 ``[T]`` 泛型参数。"""
        spec = """\
openapi: 3.1.0
info:
  title: No Generic API
  version: "1.0.0"
paths:
  /users/{user_id}:
    get:
      operationId: getUser
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
        content = (out_dir / "endpoints" / "get_user.py").read_text(encoding="utf-8")
        assert "class GetUser(APIRoute):" in content
        assert "APIRoute[" not in content
        assert "APIRoute[User]" not in content

    def test_json_decl_emits_classvar_with_model(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证 JSON decl 渲染为 ``on_<status>: ClassVar[JSONResponseSpec] = JSONResponseSpec(..., model=...)``。"""
        spec = """\
openapi: 3.1.0
info:
  title: JSON Decl API
  version: "1.0.0"
paths:
  /users/{user_id}:
    get:
      operationId: getUser
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
        content = (out_dir / "endpoints" / "get_user.py").read_text(encoding="utf-8")
        assert "on_200: ClassVar[JSONResponseSpec] = JSONResponseSpec(" in content
        assert "model=User" in content
        assert 'media_type="application/json"' in content
        assert "status_code=200" in content

    def test_raw_decl_emits_classvar_without_model(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证 Raw decl（image/png）渲染为 ``RawResponseSpec(...)``，无 ``model=`` 参数。"""
        spec = """\
openapi: 3.1.0
info:
  title: Raw Decl API
  version: "1.0.0"
paths:
  /avatars/{user_id}:
    get:
      operationId: getAvatar
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
            image/png:
              schema:
                type: string
                format: binary
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "endpoints" / "get_avatar.py").read_text(encoding="utf-8")
        assert "on_200: ClassVar[RawResponseSpec] = RawResponseSpec(" in content
        assert "model=" not in content
        assert 'media_type="image/png"' in content

    def test_default_decl_uses_callable_lambda_true(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证 ``default`` 响应渲染为 ``callable=lambda s: True``（不接受 ``status_code=``）。"""
        spec = """\
openapi: 3.1.0
info:
  title: Default API
  version: "1.0.0"
paths:
  /echo:
    post:
      operationId: postEcho
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                message:
                  type: string
      responses:
        "default":
          description: 任何状态码
          content:
            application/problem+json:
              schema:
                $ref: '#/components/schemas/Error'
components:
  schemas:
    Error:
      type: object
      required: [code]
      properties:
        code:
          type: string
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "endpoints" / "post_echo.py").read_text(encoding="utf-8")
        assert "on_default: ClassVar[JSONResponseSpec]" in content
        assert "callable=lambda s: True" in content
        assert "model=Error" in content

    def test_4xx_wildcard_decl_uses_callable_lambda_range(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证 ``4XX`` 通配符渲染为 ``callable=lambda s: 400 <= s < 500``。"""
        spec = """\
openapi: 3.1.0
info:
  title: Wildcard 4xx API
  version: "1.0.0"
paths:
  /users/{user_id}:
    get:
      operationId: getUser
      parameters:
        - name: user_id
          in: path
          required: true
          schema:
            type: string
      responses:
        "4XX":
          description: 客户端错误
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'
components:
  schemas:
    Error:
      type: object
      required: [code]
      properties:
        code:
          type: string
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "endpoints" / "get_user.py").read_text(encoding="utf-8")
        assert "on_4xx: ClassVar[JSONResponseSpec]" in content
        assert "callable=lambda s: 400 <= s < 500" in content

    def test_classvar_import_added_when_decls_exist(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证任意 decl 存在时模板注入 ``from typing import ClassVar``。"""
        spec = """\
openapi: 3.1.0
info:
  title: ClassVar Import API
  version: "1.0.0"
paths:
  /health:
    get:
      operationId: healthCheck
      responses:
        "200":
          description: ok
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: string
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "endpoints" / "health_check.py").read_text(encoding="utf-8")
        assert "from typing import ClassVar" in content

    def test_classvar_import_absent_when_no_responses(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证无响应声明时模板不输出 ``from typing import ClassVar``。

        注意：spec 仍要求 ``200`` response 存在，所以这里通过 ``description-only``
        （无 content）路径触发空 decl 列表。
        """
        spec = """\
openapi: 3.1.0
info:
  title: No Responses API
  version: "1.0.0"
paths:
  /ping:
    get:
      operationId: ping
      responses:
        "200":
          description: ok
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "endpoints" / "ping.py").read_text(encoding="utf-8")
        assert "from typing import ClassVar" not in content

    def test_json_response_spec_import_added(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证有 JSON decl 时 ``from stoma import ... JSONResponseSpec`` 自动添加。"""
        spec = """\
openapi: 3.1.0
info:
  title: JSON Import API
  version: "1.0.0"
paths:
  /users/{user_id}:
    get:
      operationId: getUser
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
        content = (out_dir / "endpoints" / "get_user.py").read_text(encoding="utf-8")
        assert "from stoma import APIRoute, JSONResponseSpec" in content
        assert "RawResponseSpec" not in content

    def test_raw_response_spec_import_added(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证有 Raw decl 时 ``from stoma import ... RawResponseSpec`` 自动添加。"""
        spec = """\
openapi: 3.1.0
info:
  title: Raw Import API
  version: "1.0.0"
paths:
  /avatars/{user_id}:
    get:
      operationId: getAvatar
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
            image/png:
              schema:
                type: string
                format: binary
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "endpoints" / "get_avatar.py").read_text(encoding="utf-8")
        assert "from stoma import APIRoute, RawResponseSpec" in content
        assert "JSONResponseSpec" not in content

    def test_mixed_json_and_raw_both_imports(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证 JSON + Raw 混合时两种 spec class 都导入。"""
        spec = """\
openapi: 3.1.0
info:
  title: Mixed Import API
  version: "1.0.0"
paths:
  /files/{file_id}:
    get:
      operationId: getFile
      parameters:
        - name: file_id
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
                $ref: '#/components/schemas/Meta'
            image/png:
              schema:
                type: string
                format: binary
components:
  schemas:
    Meta:
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
        content = (out_dir / "endpoints" / "get_file.py").read_text(encoding="utf-8")
        assert "from stoma import APIRoute, JSONResponseSpec, RawResponseSpec" in content

    def test_no_apiroute_generic_brackets_anywhere(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证整个输出文件不含 ``APIRoute[`` 残留。"""
        spec = """\
openapi: 3.1.0
info:
  title: No Generic Brackets API
  version: "1.0.0"
paths:
  /users/{user_id}:
    get:
      operationId: getUser
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
          description: not found
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'
components:
  schemas:
    User:
      type: object
      required: [id]
      properties:
        id:
          type: string
    Error:
      type: object
      required: [code]
      properties:
        code:
          type: string
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "endpoints" / "get_user.py").read_text(encoding="utf-8")
        assert "APIRoute[" not in content
        assert "APIRoute[User" not in content
        assert "APIRoute[User | Error]" not in content

    def test_response_spec_block_positioned_after_docstring(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证响应声明块在 docstring 之后、body 字段之前。

        body 字段（路径参数）的 docstring 也出现，必须确保 response_spec_decls
        不会错误地插入到 body 字段之间或之后。检查 ``on_200`` 出现在 ``user_id`` 之前。
        """
        spec = """\
openapi: 3.1.0
info:
  title: Ordering API
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
        content = (out_dir / "endpoints" / "get_user.py").read_text(encoding="utf-8")
        on_200_pos = content.index("on_200:")
        user_id_pos = content.index("user_id:")
        assert on_200_pos < user_id_pos

    def test_render_status_code_kwarg_int(self) -> None:
        """验证 ``render_status_code_kwarg`` 对 ``int`` 状态码输出 ``status_code=N``。"""
        assert render_status_code_kwarg(200) == "status_code=200"
        assert render_status_code_kwarg(404) == "status_code=404"

    def test_render_status_code_kwarg_default(self) -> None:
        """验证 ``render_status_code_kwarg`` 对 ``"default"`` 输出 ``callable=lambda s: True``。"""
        assert render_status_code_kwarg("default") == "callable=lambda s: True"

    def test_render_status_code_kwarg_range(self) -> None:
        """验证 ``render_status_code_kwarg`` 对 ``"NXX"`` 输出 ``callable=lambda s: start <= s < end``。"""
        assert render_status_code_kwarg("1XX") == "callable=lambda s: 100 <= s < 200"
        assert render_status_code_kwarg("2XX") == "callable=lambda s: 200 <= s < 300"
        assert render_status_code_kwarg("3XX") == "callable=lambda s: 300 <= s < 400"
        assert render_status_code_kwarg("4XX") == "callable=lambda s: 400 <= s < 500"
        assert render_status_code_kwarg("5XX") == "callable=lambda s: 500 <= s < 600"

    def test_render_status_code_kwarg_invalid_raises(self) -> None:
        """验证 ``render_status_code_kwarg`` 对未知字符串抛 ``ValueError``。"""
        with pytest.raises(ValueError, match="Cannot render status_code"):
            render_status_code_kwarg("6XX")
        with pytest.raises(ValueError, match="Cannot render status_code"):
            render_status_code_kwarg("XYZ")
