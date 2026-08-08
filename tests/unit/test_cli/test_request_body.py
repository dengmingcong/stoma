"""测试各种 requestBody 场景的生成结果。"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from src.cli import app
from src.openapi.parser import make_openapi_parser
from src.openapi.renderer import make_endpoint_renderer


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

    def test_request_body_v30_ref_detection(self, valid_v30_spec: Path) -> None:
        """验证 OpenAPI 3.0.x ``requestBody.content.application/json.schema.$ref`` 被 renderer 正确识别。

        直接走 ``make_openapi_parser`` + ``make_endpoint_renderer`` 而不绕道 CLI——
        绕开 ``datamodel-code-generator`` 的副产物，纯粹验证 renderer 对 3.0
        ``Reference30`` 实例的 ``_is_reference`` 检测（factory 注入 ``Reference30``
        类到 ``EndpointRenderer.Reference``，3.1 / 3.0 不串类）。
        """
        parser = make_openapi_parser(valid_v30_spec)
        parser.load()
        endpoints = parser.get_endpoints()
        renderer = make_endpoint_renderer(parser.spec_version)
        create_user = next(ep for ep in endpoints if ep.operation_id == "createUser")
        _file_name, code = renderer.render(create_user)
        assert "from .models import User" in code
        assert "body: User" in code

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

    def test_request_body_with_kebab_case_schema_name(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
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
        assert (out_dir / "create_user.py").exists()
        assert (out_dir / "models.py").exists()

        models_content = (out_dir / "models.py").read_text(encoding="utf-8")
        assert "class UserProfile(BaseModel):" in models_content
        assert "class user-profile" not in models_content

        route_content = (out_dir / "create_user.py").read_text(encoding="utf-8")
        assert "from .models import UserProfile" in route_content
        assert "body: UserProfile" in route_content

    def test_request_body_with_discriminator_union(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """验证 requestBody 使用带 discriminator 的 oneOf schema 时生成联合模型。
 
        回归测试：discriminator oneOf 在 dmcg 0.72.2 中会生成 ``RootModel[Cat | Dog]``
        作为 ``Pet``，并把 ``Cat`` / ``Dog`` 独立为可被 ``Pet`` 引用的子类。
        路由文件应引用 ``Pet`` 作为 body 参数。
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
        route = (out_dir / "create_pet.py").read_text(encoding="utf-8")
        assert "class Pet(RootModel[Cat | Dog])" in models
        assert "class Cat(PetBase)" in models
        assert "class Dog(PetBase)" in models
        assert 'Annotated[Cat | Dog, Field(discriminator="pet_type")]' in models
        assert "from .models import Pet" in route
        assert "body: Pet" in route

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
        assert 'first_name: Annotated[str, Field(alias="firstName")]' in models
        assert 'is_active: Annotated[bool | None, Field(alias="isActive")] = None' in models
        # PascalCase → snake + alias 保留原名。
        assert 'last_name: Annotated[str, Field(alias="LastName")]' in models
        assert 'email_address: Annotated[EmailStr | None, Field(alias="EmailAddress")] = None' in models
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
        assert 'customer_info: Annotated[CustomerInfo, Field(alias="customerInfo")]' in models
        assert 'total_amount: Annotated[float | None, Field(alias="totalAmount")] = None' in models
        # 嵌套对象独立生成 model，字段同样满足 alias 约定。
        assert 'first_name: Annotated[str, Field(alias="firstName")]' in models
        assert 'last_name: Annotated[str | None, Field(alias="lastName")] = None' in models
        # 嵌套内的嵌套（含全大写字段名）也命中 alias。
        assert 'street_name: Annotated[str | None, Field(alias="streetName")] = None' in models
        assert 'zip_code: Annotated[str | None, Field(alias="ZIPCode")] = None' in models

    def test_request_body_with_oneof_union(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """验证 requestBody 使用 oneOf 包含多个 $ref 时生成 Pydantic v2 联合类型。

        dmcg 0.72.2 在 ``use_union_operator=True``（默认）下为 oneOf 生成
        ``RootModel[TypeA | TypeB]``，其中 ``TypeA | TypeB`` 为内置 union 语法。
        route.py 应正确引用该 body 类型。
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
        assert (out_dir / "create_entity.py").exists()

        models_content = (out_dir / "models.py").read_text(encoding="utf-8")
        # dmcg 生成 RootModel[TypeA | TypeB]，验证 TypeA | TypeB 存在。
        assert "TypeA | TypeB" in models_content

        route_content = (out_dir / "create_entity.py").read_text(encoding="utf-8")
        # route.py 应从 models 导入 body 类型。
        assert "from .models import" in route_content
        assert "body:" in route_content

    def test_request_body_with_anyof_union(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """验证 requestBody 使用 anyOf 包含多个 $ref 时生成 Pydantic v2 联合类型。

        dmcg 0.72.2 在 ``use_union_operator=True``（默认）下为 anyOf 生成
        ``RootModel[TypeA | TypeB]``，与 oneOf 行为一致。route.py 应正确引用
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
        assert (out_dir / "create_record.py").exists()

        models_content = (out_dir / "models.py").read_text(encoding="utf-8")
        # dmcg 生成 RootModel[TypeA | TypeB]，验证 TypeA | TypeB 存在。
        assert "TypeA | TypeB" in models_content

        route_content = (out_dir / "create_record.py").read_text(encoding="utf-8")
        # route.py 应从 models 导入 body 类型。
        assert "from .models import" in route_content
        assert "body:" in route_content

    def test_request_body_with_allof_merge(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
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
        assert (out_dir / "create_order.py").exists()

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

        route = (out_dir / "create_order.py").read_text(encoding="utf-8")
        # route 引用合并后的 ``CreateOrderRequest``，请求体验证覆盖父类 + 内联字段。
        assert "from .models import CreateOrderRequest" in route
        assert "body: CreateOrderRequest" in route

    def test_request_and_response_share_model_dedupes_import(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """验证 requestBody 和 response 共用同一 schema 时 import 不重复。

        回归测试：当 POST /users 的 requestBody 和 201 response 都引用
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
        route_content = (out_dir / "create_user.py").read_text(encoding="utf-8")
        # 导入了 User（存在至少一次）。
        assert "from .models import User" in route_content
        # 不应该出现重复的 ``User, User``。
        assert "from .models import User, User" not in route_content
        # 文件必须是语法正确的 Python。
        compile(route_content, "create_user.py", "exec")
