"""``src.openapi.parameters``（含 ``make_param_fields`` 渲染管线）的端到端单元测试。

迁移自 :mod:`tests.unit.test_cli.test_parameters` —— 之前被混入 ``test_cli/``
包内，但实际验证的是 :mod:`src.openapi.parameters` 在 OpenAPI ``parameters``
字段上的派生结果（query / path / header、``$ref`` 解析、链式 ``$ref``、环引用、
外部 ref、path item 级 ``parameters`` 合并与继承）。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.cli import app


class TestMakeParameters:
    """测试各种 parameter 场景的生成结果。"""

    def test_query_parameters_with_types(self, cli_runner: Any, tmp_path: Path) -> None:
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

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "search.py").read_text(encoding="utf-8")
        # Python 类型映射正确。
        assert "q: str" in content
        assert "limit: int | None = None" in content
        assert "score: float | None = None" in content
        assert "active: bool | None = None" in content

    def test_header_parameter_uses_annotated(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证 header 参数使用 ``Annotated[..., Header(...)]`` 标记。

        非 snake_case 参数会被转为 snake_case 并通过 ``Field(serialization_alias=...)``
        保留原名。
        """
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

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "check_auth.py").read_text(encoding="utf-8")
        # header 参数使用 ``Annotated[..., Header(...)]`` 标记。
        assert "from stoma import APIRouter, APIRoute, Header" in content
        # models 来自 .models 导入，所以这里只需要 Field（不再内联 BaseModel 定义）。
        assert "from pydantic import Field" in content
        assert "from typing import Annotated" in content
        # required header 参数：转为 snake_case + Annotated[..., Header(), Field(serialization_alias=...)]
        assert "authorization: Annotated[str, Header(), Field(serialization_alias='Authorization')]" in content
        # non-required header 参数：转为 snake_case + Annotated[..., Header(), Field(serialization_alias=...)] = None
        assert (
            "x_request_id: Annotated[str | None, Header(), Field(serialization_alias='X-Request-ID')] = None" in content
        )

    def test_required_vs_optional_path_param(self, cli_runner: Any, tmp_path: Path) -> None:
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

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "get_item.py").read_text(encoding="utf-8")
        assert "item_id: str" in content
        # required 参数不应有 = None 默认值。
        assert "item_id: str = None" not in content

    def test_parameter_ref_resolves(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证 spec 中 ``components.parameters`` 的 ``$ref`` 能被解析并生成正确字段。"""
        spec = """\
openapi: 3.1.0
info:
  title: Ref API
  version: "1.0.0"
components:
  parameters:
    PageSize:
      name: page
      in: query
      schema:
        type: integer
paths:
  /items:
    get:
      operationId: listItems
      parameters:
        - $ref: '#/components/parameters/PageSize'
      responses:
        "200":
          description: ok
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "list_items.py").read_text(encoding="utf-8")
        assert "page: int | None = None" in content

    def test_parameter_v30_ref_detection(self, cli_runner: Any, valid_v30_spec: Path) -> None:
        """验证 OpenAPI 3.0.x ``parameters[*].$ref`` 被 CLI 正确解析。

        ``components.parameters.UserIdParam`` 定义 ``schema: type: string``，
        解析后应映射为 ``str`` 而不是把 ref 末段 ``UserIdParam`` 当作类型名。
        """
        out_dir = valid_v30_spec.parent / "output"

        result = cli_runner.invoke(app, [str(valid_v30_spec), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "get_user.py").read_text(encoding="utf-8")
        assert "user_id: str" in content
        assert "user_id: UserIdParam" not in content

    def test_parameter_ref_chained_resolves(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证 A → B → C 三层链式 ref 能递归解析到 C。"""
        spec = """\
openapi: 3.1.0
info:
  title: Chained Ref API
  version: "1.0.0"
components:
  parameters:
    C:
      name: page
      in: query
      schema:
        type: integer
    B:
      $ref: '#/components/parameters/C'
    A:
      $ref: '#/components/parameters/B'
paths:
  /items:
    get:
      operationId: listItems
      parameters:
        - $ref: '#/components/parameters/A'
      responses:
        "200":
          description: ok
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "list_items.py").read_text(encoding="utf-8")
        assert "page: int | None = None" in content

    def test_parameter_cycle_raises(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证 ``components.parameters.A -> B -> A`` 环引用被 CLI 捕获并报告。

        经 ``make_openapi_parser`` 在工厂层做 cycle 检测，遇到环立即抛
        :class:`OpenAPISchemaError`，经 CLI 包装为非 0 退出码并把错误信息
        打到 ``result.output``。断言必须看到完整环路径 ``"A -> B -> A"``，
        而不是仅看到 "Cycle detected" 关键字。
        """
        spec = """\
openapi: 3.1.0
info:
  title: Cycle API
  version: "1.0.0"
components:
  parameters:
    A:
      $ref: '#/components/parameters/B'
    B:
      $ref: '#/components/parameters/A'
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

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)], catch_exceptions=False)

        assert result.exit_code != 0
        assert "Cycle detected in parameter $ref chain" in result.output
        assert "A -> B -> A" in result.output

    def test_parameter_external_ref_raises(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证指向外部文件的 ``$ref``（如 ``common.yaml#/schemas/X``）被 CLI 捕获并报告。

        :func:`expand_path_refs` 委托 :mod:`jsonref` 解析，jsonref 抛
        :class:`jsonref.JsonRefError` 时被包装为 :class:`OpenAPISchemaError`，
        CLI 退出码非 0 并把 "Failed to resolve parameter or requestBody $ref" 打到输出。
        """
        spec = """\
openapi: 3.1.0
info:
  title: External Ref API
  version: "1.0.0"
paths:
  /items:
    get:
      operationId: listItems
      parameters:
        - name: x
          in: query
          schema:
            $ref: 'common.yaml#/schemas/X'
      responses:
        "200":
          description: ok
"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(spec, encoding="utf-8")
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)], catch_exceptions=False)

        assert result.exit_code != 0
        assert "Failed to resolve parameter or requestBody $ref" in result.output

    def test_parameter_cycle_not_referenced_still_raises(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证 ``components.parameters`` 中的环即使没被任何 path 引用也被检测到。

        :func:`src.openapi.reference.validate_cycle_refs` 是对整张
        ``components.parameters`` 表做 DFS，而不是只走被引用的子图；任何
        ``$ref`` 闭环都会立即抛 :class:`OpenAPISchemaError`。场景里 path 不带
        ``parameters``，只用 ``responses`` 占位——确保 C / D 不会被任何 path 触达，
        cycle 检测仍然命中。
        """
        spec = """\
openapi: 3.1.0
info:
  title: Unreferenced Cycle API
  version: "1.0.0"
components:
  parameters:
    C:
      $ref: '#/components/parameters/D'
    D:
      $ref: '#/components/parameters/C'
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

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)], catch_exceptions=False)

        assert result.exit_code != 0
        assert "Cycle detected in parameter $ref chain" in result.output
        assert "C -> D -> C" in result.output

    def test_path_item_parameters_merged_with_override(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证 path_item 级 + operation 级同名覆盖 + path_item 级独占继承同时工作。

        场景：

        - path_item.parameters：
          - X-Tenant-ID（required=true）  → 会被 operation 覆盖
          - Authorization（required=true） → path_item 独占，operation 没 override
        - operation.parameters：
          - X-Tenant-ID（required=false）  → 覆盖 path_item 级同名
          - q（query）                     → operation 独占

        修复后输出含 4 个字段断言（X-Tenant-ID 用 op 覆盖值、Authorization 继承、
        q 是 op 独有）。
        bug 状态下（没合并 path_item）只有 2 个（X-Tenant-ID 用 op 覆盖、q 是 op 独有），
        缺少 Authorization。
        """
        spec = """\
openapi: 3.1.0
info:
  title: Merge API
  version: "1.0.0"
paths:
  /items:
    parameters:
      - name: X-Tenant-ID
        in: header
        required: true
        schema:
          type: string
      - name: Authorization
        in: header
        required: true
        schema:
          type: string
    get:
      operationId: listItems
      parameters:
        - name: X-Tenant-ID
          in: header
          required: false
          schema:
            type: string
        - name: q
          in: query
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
        content = (out_dir / "list_items.py").read_text(encoding="utf-8")
        # 1. operation 级覆盖 path_item 级 X-Tenant-ID（required=False）
        assert (
            "x_tenant_id: Annotated[str | None, Header(), Field(serialization_alias='X-Tenant-ID')] = None" in content
        )
        # 2. path_item 级 Authorization 被 operation 继承（required=True）
        assert "authorization: Annotated[str, Header(), Field(serialization_alias='Authorization')]" in content
        # 3. operation 级独有的 q
        assert "q: str | None = None" in content

    def test_path_item_parameters_inherited_when_no_operation_override(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证 operation 没 override 时，path_item 级参数被自动继承。

        path_item 级 X-Tenant-ID (required=true)，operation 没 parameters → 继承后
        生成的字段是 str（required=True 的渲染，不带 | None，不带 default）。
        """
        spec = """\
openapi: 3.1.0
info:
  title: Inherit API
  version: "1.0.0"
paths:
  /items:
    parameters:
      - name: X-Tenant-ID
        in: header
        required: true
        schema:
          type: string
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
        content = (out_dir / "list_items.py").read_text(encoding="utf-8")
        # 继承 path_item 级，required=True → str（无 | None，无 default）
        assert "x_tenant_id: Annotated[str, Header(), Field(serialization_alias='X-Tenant-ID')]" in content
