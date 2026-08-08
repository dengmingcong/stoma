"""测试各种 parameter 场景的生成结果。"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from src.cli import app
from src.openapi.parser import OpenAPISchemaError, make_openapi_parser
from src.openapi.renderer import make_endpoint_renderer


class TestMakeParameters:
    """测试各种 parameter 场景的生成结果。"""

    def test_query_parameters_with_types(self, cli_runner: CliRunner, tmp_path: Path) -> None:
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

    def test_header_parameter_uses_annotated(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """验证 header 参数使用 Annotated[..., Header(...)] 标记。

        非 snake_case 参数会被转为 snake_case 并通过 Field(serialization_alias=...) 保留原名。
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
        # header 参数使用 Annotated[..., Header(...)] 标记。
        assert "from stoma import APIRouter, APIRoute, Header" in content
        # models 来自 .models 导入，所以这里只需要 Field（不再内联 BaseModel 定义）。
        assert "from pydantic import Field" in content
        assert "from typing import Annotated" in content
        # required header 参数：转为 snake_case + Field(serialization_alias=...)
        assert "authorization: Annotated[str, Header()] = Field(serialization_alias='Authorization')" in content
        # non-required header 参数：转为 snake_case + Field(default=None, serialization_alias=...)
        assert (
            "x_request_id: Annotated[str | None, Header()] = Field(default=None, serialization_alias='X-Request-ID')"
            in content
        )

    def test_required_vs_optional_path_param(self, cli_runner: CliRunner, tmp_path: Path) -> None:
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

    def test_parameter_ref_resolves(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """验证 spec 中 components.parameters 的 $ref 能被解析并生成正确字段。"""
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

    def test_parameter_v30_ref_detection(self, valid_v30_spec: Path) -> None:
        """验证 OpenAPI 3.0.x ``parameters[*].$ref`` 被 parser + renderer 正确解析。

        ``components.parameters.UserIdParam`` 定义 ``schema: type: string``，
        解析后 ``param_schema`` 应是 ``Schema``（不是 ``Reference30``），
        renderer 才能映射为 ``str`` 而不是把 ref 末段 ``UserIdParam`` 当作类型名。
        """
        parser = make_openapi_parser(valid_v30_spec)
        parser.load()
        endpoints = parser.get_endpoints()
        renderer = make_endpoint_renderer(parser.spec_version)
        get_user = next(ep for ep in endpoints if ep.operation_id == "getUser")
        _file_name, code = renderer.render(get_user)
        assert "user_id: str" in code
        assert "user_id: UserIdParam" not in code

    def test_parameter_ref_chained_resolves(self, cli_runner: CliRunner, tmp_path: Path) -> None:
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

    def test_parameter_ref_cycle_raises(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """验证 A ↔ B 环引用被检测并抛 OpenAPISchemaError（绕开 CLI 包装验原始错误）。

        直接调 :meth:`OpenAPIParser.resolve_parameter_refs` 而不走 CLI，是因为 bug 状态下 Reference
        透传到 renderer 也会触发 AttributeError 让 ``exit_code != 0``，验退出码抓不到
        真正的 cycle 检测逻辑。
        """
        from openapi_pydantic import Reference

        spec_file = tmp_path / "cycle.yaml"
        spec_file.write_text(
            "openapi: 3.1.0\n"
            "info:\n"
            "  title: Cycle test\n"
            '  version: "1.0.0"\n'
            "paths: {}\n"
            "components:\n"
            "  parameters:\n"
            "    A:\n"
            "      $ref: '#/components/parameters/B'\n"
            "    B:\n"
            "      $ref: '#/components/parameters/A'\n",
            encoding="utf-8",
        )
        parser = make_openapi_parser(spec_file)
        parser.load()

        ref_params: list[Reference] = [Reference.model_validate({"$ref": "#/components/parameters/A"})]
        with pytest.raises(OpenAPISchemaError, match="Cycle detected"):
            parser.resolve_parameter_refs(parser.raw_spec_dict, ref_params)

    def test_parameter_ref_external_raises(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """验证外部 ref（common.yaml#/...）被拒绝并抛 OpenAPISchemaError。

        直接调 :meth:`OpenAPIParser.resolve_parameter_refs` 而不走 CLI，原因同 cycle 测试 —— 验
        退出码抓不到 parser 层对 ``#/components/parameters/`` 前缀的检查。
        """
        from openapi_pydantic import Reference

        spec_file = tmp_path / "ext.yaml"
        spec_file.write_text(
            'openapi: 3.1.0\ninfo:\n  title: External ref test\n  version: "1.0.0"\npaths: {}\n',
            encoding="utf-8",
        )
        parser = make_openapi_parser(spec_file)
        parser.load()

        ref_params: list[Reference] = [Reference.model_validate({"$ref": "common.yaml#/parameters/X"})]
        with pytest.raises(OpenAPISchemaError, match=r"Unsupported parameter \$ref"):
            parser.resolve_parameter_refs(parser.raw_spec_dict, ref_params)

    def test_path_item_parameters_merged_with_override(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """验证 path_item 级 + operation 级同名覆盖 + path_item 级独占继承同时工作。

        场景：
        - path_item.parameters：
          - X-Tenant-ID（required=true）  → 会被 operation 覆盖
          - Authorization（required=true） → path_item 独占，operation 没 override
        - operation.parameters：
          - X-Tenant-ID（required=false）  → 覆盖 path_item 级同名
          - q（query）                     → operation 独占

        修复后输出含 4 个字段断言（X-Tenant-ID 用 op 覆盖值、Authorization 继承、q 是 op 独有）。
        bug 状态下（没合并 path_item）只有 2 个（X-Tenant-ID 用 op 覆盖、q 是 op 独有），缺少 Authorization。
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
            "x_tenant_id: Annotated[str | None, Header()] = Field(default=None, serialization_alias='X-Tenant-ID')"
            in content
        )
        # 2. path_item 级 Authorization 被 operation 继承（required=True）
        assert "authorization: Annotated[str, Header()] = Field(serialization_alias='Authorization')" in content
        # 3. operation 级独有的 q
        assert "q: str | None = None" in content

    def test_path_item_parameters_inherited_when_no_operation_override(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
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
        assert "x_tenant_id: Annotated[str, Header()] = Field(serialization_alias='X-Tenant-ID')" in content
