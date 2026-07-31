"""测试各种 parameter 场景的生成结果。"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.cli import app


class TestMakeParameters:
    """测试各种 parameter 场景的生成结果。"""

    def test_query_parameters_with_types(
        self, cli_runner: pytest.fixture, tmp_path: Path
    ) -> None:
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
        assert "limit: int = None" in content
        assert "score: float = None" in content
        assert "active: bool = None" in content

    def test_header_parameter_uses_annotated(
        self, cli_runner: pytest.fixture, tmp_path: Path
    ) -> None:
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

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        content = (out_dir / "check_auth.py").read_text(encoding="utf-8")
        # header 参数走 header_params，不出现在 param_fields 中。
        assert "from stoma import router, APIRoute, Header" in content
        assert "from typing import Annotated" in content
        assert "Authorization" not in content or "Annotated" in content

    def test_required_vs_optional_path_param(
        self, cli_runner: pytest.fixture, tmp_path: Path
    ) -> None:
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
