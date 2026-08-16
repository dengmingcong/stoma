"""测试各种 response body 场景的生成结果。"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from src.cli import app
from src.openapi.parser import make_openapi_parser
from src.openapi.renderer import make_endpoint_renderer


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
        assert "from .models import User" in code
        assert "APIRoute[User]" in code

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
        assert 'widget_id: Annotated[str, Field(alias="widgetId")]' in models
        assert 'widget_name: Annotated[str, Field(alias="widgetName")]' in models
        # PascalCase → snake + alias 保留原名。
        assert 'created_at: Annotated[AwareDatetime | None, Field(alias="CreatedAt")] = None' in models
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
        assert 'order_info: Annotated[OrderInfo, Field(alias="orderInfo")]' in models
        assert 'total_amount: Annotated[float | None, Field(alias="totalAmount")] = None' in models
        # 嵌套对象独立生成 model，字段同样满足 alias 约定。
        assert 'order_id: Annotated[str, Field(alias="orderId")]' in models
        # 嵌套内的嵌套（含全大写字段名）也命中 alias。
        assert 'street_name: Annotated[str | None, Field(alias="streetName")] = None' in models
        assert 'zip_code: Annotated[str | None, Field(alias="ZIPCode")] = None' in models

    def test_response_with_oneof_union(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """验证 response 使用 oneOf 引用多个 schema 时生成 union 类型。

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
        route = (out_dir / "get_entity.py").read_text(encoding="utf-8")
        # dmcg 将 oneOf 包装为 RootModel[TypeA | TypeB]。
        assert "TypeA | TypeB" in models
        # 由 use_operation_id_as_name 派生响应包装类。
        assert "GetEntityResponse" in models
        assert "RootModel[TypeA | TypeB]" in models
        # route.py 正确引用包装类。
        assert "APIRoute[GetEntityResponse]" in route
        assert "from .models import GetEntityResponse" in route

    def test_response_with_anyof_union(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """验证 response 使用 anyOf 引用多个 schema 时生成 union 类型。

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
        route = (out_dir / "get_record.py").read_text(encoding="utf-8")
        # dmcg 将 anyOf 包装为 RootModel[TypeA | TypeB]。
        assert "TypeA | TypeB" in models
        # 由 use_operation_id_as_name 派生响应包装类。
        assert "GetRecordResponse" in models
        assert "RootModel[TypeA | TypeB]" in models
        # route.py 正确引用包装类。
        assert "APIRoute[GetRecordResponse]" in route
        assert "from .models import GetRecordResponse" in route

    def test_response_with_multiple_status_codes_union(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
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
        route = (out_dir / "get_user.py").read_text(encoding="utf-8")
        # 泛型拼接为 PEP 604 union，按 spec 顺序 ``User`` 在 ``Error`` 前。
        assert "APIRoute[User | Error]" in route
        # import 行包含两个模型名（顺序亦对齐 spec 出现顺序）。
        assert "from .models import User, Error" in route
        # 防御：当前实现若把 ``response_type`` 当字符串迭代（``U | s | e | r`` 之类）
        # 而不是真正的 Union，会被这两个断言同时挡下。
        assert "U | s | e | r" not in route

    def test_response_with_duplicate_status_codes_dedup(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
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
        route = (out_dir / "create_user.py").read_text(encoding="utf-8")
        # 单一 ``User`` 泛型，不出现 ``User | User``。
        assert "APIRoute[User]" in route
        assert "APIRoute[User | User]" not in route
        # import 行 ``User`` 只出现一次：先验整行，再验逐项计数。
        assert "from .models import User" in route
        assert route.count("from .models import User") == 1
        # 防御：import 行不冗余成 ``User, User``。
        assert "import User, User" not in route

    def test_response_with_mixed_json_and_non_json_status(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
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
        route = (out_dir / "get_user.py").read_text(encoding="utf-8")
        # 400 没有 JSON content,被跳过,泛型保持单元素 ``User``。
        assert "APIRoute[User]" in route
        # 不应出现 ``User | None`` 或别的拼接污染。
        assert "User | None" not in route
        assert "User | " not in route
        assert "from .models import User" in route

    def test_response_with_only_non_json_status_codes(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """验证所有 status 都只有 description、无 application/json 时,route 保持裸 ``APIRoute)``。

        行为契约：
        - 所有 status 均无 ``application/json`` content（典型：纯 health check 接口）。
        - 不输出 ``APIRoute[...]`` 泛型语法,保持裸 ``APIRoute)``。
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
        route = (out_dir / "health_check.py").read_text(encoding="utf-8")
        # 裸 ``APIRoute)``,无泛型参数。
        assert "APIRoute)" in route
        # 不输出 ``APIRoute[...]`` 形式。
        assert "APIRoute[" not in route
        # 没有响应模型可 import,不应有 ``from .models import ...`` 行。
        assert "from .models import" not in route

    def test_response_with_three_status_codes_union(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """验证 200 + 400 + 500 三个 ``$ref`` 都参与 Union,且 import 行三个都列出。

        行为契约：
        - 三个 JSON status 都进入 ``APIRoute[...]``,按 spec 顺序拼接成 pipe union。
        - ``from .models import ...`` 行包含全部三个模型名。
        - 验证不仅测首尾,中间元素 ``Error`` 也必须在两个断言里都出现。
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
        route = (out_dir / "get_user.py").read_text(encoding="utf-8")
        # 三个模型按 spec 顺序 pipe-union。
        assert "APIRoute[User | Error | ServerError]" in route
        # import 行同时列出全部三个,且顺序与泛型一致。
        assert "from .models import User, Error, ServerError" in route

    def test_response_with_inline_multi_status_uses_counter_suffix(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """验证多个 inline 响应用 dmcg 计数器后缀（``GetXResponse`` / ``GetXResponse1``）。

        行为契约：
        - dmcg 对多个 inline response 按 ``{OpId}Response`` / ``{OpId}Response1``
          计数器命名（``use_operation_id_as_name=True``）。
        - renderer 必须镜像同一规则,否则 inline 错误响应模型会被丢弃。
        - ``APIRoute[...]`` 同时引用 ``GetXResponse`` 和 ``GetXResponse1``。
        - ``from .models import ...`` 行同时列出两者。
        - 计数器从 1 开始（不是 0）,与 dmcg ``openapi.py:_parse_schema_or_ref``
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
        route = (out_dir / "get_x.py").read_text(encoding="utf-8")
        # dmcg 已经按计数器命名生成两个 model：第一个 ``GetXResponse``,
        # 第二个 ``GetXResponse1``（不是 ``GetXResponse2``,不是 ``GetXErrorResponse``）。
        assert "class GetXResponse" in models
        assert "class GetXResponse1" in models
        # ``GetXResponse2`` 不应出现（只有两个 inline response）。
        assert "class GetXResponse2" not in models
        # route.py 同时引用两个 inline 模型,顺序与 spec 一致。
        assert "APIRoute[GetXResponse | GetXResponse1]" in route
        # import 行同时列出两者。
        assert "from .models import GetXResponse, GetXResponse1" in route

    def test_response_with_mixed_ref_and_inline_multi_status(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """验证 200 ``$ref User`` + 400/500 inline 时 ``$ref`` 不消耗 inline 计数器。

        行为契约：
        - dmcg 对 ``$ref`` 走 ``resolve_ref`` 短路,inline 命名从 1 开始,不受 ``$ref`` 影响。
        - renderer 必须镜像:``$ref`` 不消耗 inline 计数器,inline 仍命名为
          ``GetXResponse`` / ``GetXResponse1``。
        - ``APIRoute[...]`` 顺序为 spec 出现顺序:``User`` (200) → ``GetXResponse`` (400) → ``GetXResponse1`` (500)。
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
        route = (out_dir / "get_x.py").read_text(encoding="utf-8")
        # dmcg 行为：$ref 不消耗计数器,所以 inline 仍从 ``GetXResponse`` 开始。
        assert "class GetXResponse" in models
        assert "class GetXResponse1" in models
        # 防御：inline 计数器若错从 2 开始（误以为 ``$ref`` 占位）,
        # 会生成 ``GetXResponse2`` 而不是 ``GetXResponse1``,或反过来跳过 ``GetXResponse1``。
        assert "class GetXResponse2" not in models
        # route.py 按 spec 顺序拼接：
        # ``User`` ($ref 200) → ``GetXResponse`` (inline 400) → ``GetXResponse1`` (inline 500)。
        assert "APIRoute[User | GetXResponse | GetXResponse1]" in route
        # import 行同步列出全部三个,顺序与泛型一致。
        assert "from .models import User, GetXResponse, GetXResponse1" in route

    def test_response_with_only_error_status_codes_generates_models(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """验证仅有 4xx/5xx JSON 响应（无 200/201）时仍生成 ``models.py`` 与对应 route import。

        行为契约：
        - spec 仅声明 ``400`` + ``500`` 两种 JSON 响应、没有 ``200``/``201`` 成功
          响应,且 ``components.schemas`` 故意为空（只有 ``$ref`` 指向的占位
          名）——目的是把模型生成的唯一开关留给 ``parser.has_json_payloads``,
          而不是 ``components.schemas`` 兜底分支。
        - ``parser.has_json_payloads`` 必须为 ``True``（与 renderer 对所有 JSON status
          一视同仁保持一致）,CLI 必须生成 ``models.py``,并由 route 文件引用
          两个错误模型。
        - 这是 ``src/openapi/parser.py:get_endpoints`` 中 ``has_json_payloads`` 过滤器
          从 ``{"200", "201"}`` 改为"全部 status"后的一致性回归锁。
        - 防御：若 ``has_json_payloads`` 过滤器未更新,CLI 会跳过 ``models.py``
          生成,但 route 仍生成 ``from .models import Error, ServerError`` ——导入
          指向不存在的文件,运行时 ``ImportError``。本测试在生成阶段就拦截
          这种「silent missing import」漂移。

        设计说明：
        - ``$ref`` 指向 ``#/components/schemas/Error`` 等是 *dangling ref*;
          openapi-pydantic 加载期不验证,datamodel-code-generator 会发出
          ``DanglingRefWarning`` 并生成 ``class Error(RootModel[Any])`` 占位,
          满足断言 ``class Error in models`` / ``class ServerError in models``。
        - 这样 spec 仍然合法、可加载,但 ``components.schemas`` 是空 dict,
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
            "models.py 未生成 ——parser.has_json_payloads 在仅有错误响应时仍为 False,"
            "CLI 跳过了 generate_models 调用"
        )
        models = (out_dir / "models.py").read_text(encoding="utf-8")
        assert "class Error" in models
        assert "class ServerError" in models
        # route.py 引用两个错误模型(顺序对齐 spec 出现顺序:Error 在前,ServerError 在后)。
        route = (out_dir / "get_user.py").read_text(encoding="utf-8")
        assert "APIRoute[Error | ServerError]" in route
        assert "from .models import Error, ServerError" in route

    def test_parser_has_json_payloads_true_when_only_error_responses(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """直接走 parser 探测 ``has_json_payloads``,验证错误响应纳入判定。

        行为契约：
        - 与 ``test_response_with_only_error_status_codes_generates_models``
          互补,直接走 ``make_openapi_parser`` 验证 ``parser.has_json_payloads``
          属性值,避免 CLI 副作用掩盖判定错误。
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
        assert parser.has_json_payloads is True, (
            "parser.has_json_payloads 应为 True ——4xx/5xx JSON 响应必须纳入判定"
        )
