"""``src.openapi.reference`` 的单元测试。

迁移自 :mod:`tests.unit.test_model_generator` 中的
:class:`TestExpandPathRefs` 与 :class:`TestValidateCycleRefs` —— 之前被混入
``test_model_generator.py``，但实际测试的是 :mod:`src.openapi.reference` 模块。
"""

from typing import Any

import pytest

from stoma.exceptions import OpenAPISchemaError
from stoma.openapi.reference import expand_path_refs, validate_cycle_refs


class TestExpandPathRefs:
    """测试 :func:`expand_path_refs` 选择性参数 ``$ref`` 展开。"""

    def test_expand_path_refs_preserves_body_refs(self) -> None:
        """``responses`` 中的 ``$ref`` 字符串保持原样（``requestBody`` 已被抽离）。

        :func:`expand_path_refs` 仅展开 ``parameters`` 与 ``requestBody`` 中的 ``$ref``；
        展开后的 ``requestBody`` 抽离到返回的 ``request_body_map``，原始 spec
        中的 ``requestBody`` 保持 ``$ref`` 字符串原样；``responses``、``summary``
        等字段在合成 spec 中被丢弃，原样 spec 中保持不变。
        """
        spec: dict[str, Any] = {
            "paths": {
                "/items": {
                    "get": {
                        "operationId": "listItems",
                        "parameters": [{"$ref": "#/components/parameters/PageParam"}],
                        "requestBody": {"$ref": "#/components/schemas/ItemBody"},
                        "responses": {
                            "200": {"$ref": "#/components/responses/ItemList"},
                            "404": {"$ref": "#/components/responses/NotFound"},
                        },
                        "summary": "list summary",
                    }
                }
            },
            "components": {
                "parameters": {
                    "PageParam": {
                        "name": "page",
                        "in": "query",
                        "schema": {"type": "integer"},
                    }
                },
                "schemas": {"ItemBody": {"type": "object"}},
                "responses": {
                    "ItemList": {"description": "ok"},
                    "NotFound": {"description": "missing"},
                },
            },
        }

        result, _request_body_map = expand_path_refs(spec)

        expanded_param = result["paths"]["/items"]["get"]["parameters"][0]
        assert expanded_param == {
            "name": "page",
            "in": "query",
            "schema": {"type": "integer"},
        }
        assert "$ref" not in expanded_param
        assert result["paths"]["/items"]["get"]["requestBody"] == {"$ref": "#/components/schemas/ItemBody"}
        assert result["paths"]["/items"]["get"]["responses"] == {
            "200": {"$ref": "#/components/responses/ItemList"},
            "404": {"$ref": "#/components/responses/NotFound"},
        }
        assert result["paths"]["/items"]["get"]["summary"] == "list summary"

    def test_expand_path_refs_resolves_parameter_chain(self) -> None:
        """``parameters[*].$ref`` 指向 ``#/components/parameters/X`` 时被展开。"""
        spec: dict[str, Any] = {
            "paths": {"/items": {"get": {"parameters": [{"$ref": "#/components/parameters/PageParam"}]}}},
            "components": {
                "parameters": {
                    "PageParam": {
                        "name": "page",
                        "in": "query",
                        "schema": {"type": "integer"},
                    }
                }
            },
        }

        result, _request_body_map = expand_path_refs(spec)

        assert result["paths"]["/items"]["get"]["parameters"] == [
            {"name": "page", "in": "query", "schema": {"type": "integer"}}
        ]

    def test_expand_path_refs_catches_external_ref_error(self) -> None:
        """组件参数 ``schema.$ref`` 指向外部文件时抛出 :class:`OpenAPISchemaError`。"""
        spec: dict[str, Any] = {
            "paths": {"/x": {"get": {"parameters": [{"$ref": "#/components/parameters/X"}]}}},
            "components": {
                "parameters": {
                    "X": {
                        "name": "x",
                        "in": "query",
                        "schema": {"$ref": "common.yaml#/components/schemas/Common"},
                    }
                }
            },
        }

        with pytest.raises(OpenAPISchemaError, match=r"Failed to resolve parameter or requestBody \$ref"):
            expand_path_refs(spec)

    def test_expand_path_refs_resolves_path_item_level_ref(self) -> None:
        """path item 级 ``parameters`` 中的 ``$ref`` 也应被展开。

        OpenAPI 允许 ``parameters`` 直接挂在 ``paths[/x]`` 上（对所有 method 生效），
        而非只在 ``paths[/x][<method>]`` 上。回归测试：路径项级 ``$ref`` 必须
        走到 jsonref，回写后 ``raw_spec`` 中该列表里 ``$ref`` 已替换。
        """
        spec: dict[str, Any] = {
            "paths": {
                "/items": {
                    "parameters": [
                        {"$ref": "#/components/parameters/X-Tenant-ID"},
                    ],
                    "get": {
                        "operationId": "listItems",
                        "responses": {"200": {"description": "ok"}},
                    },
                }
            },
            "components": {
                "parameters": {
                    "X-Tenant-ID": {
                        "name": "X-Tenant-ID",
                        "in": "header",
                        "required": True,
                        "schema": {"type": "string"},
                    },
                },
            },
        }

        result, _request_body_map = expand_path_refs(spec)

        expanded = result["paths"]["/items"]["parameters"][0]
        assert "$ref" not in expanded
        assert expanded == {
            "name": "X-Tenant-ID",
            "in": "header",
            "required": True,
            "schema": {"type": "string"},
        }
        # operation 级不应被误植 parameters（也没声明过）。
        assert "parameters" not in result["paths"]["/items"]["get"]


class TestValidateCycleRefs:
    """测试 :func:`src.openapi.reference.validate_cycle_refs` 参数 ``$ref`` 环检测。"""

    def test_validate_cycle_refs_raises_on_cycle(self) -> None:
        """``A -> B -> A`` 的环应抛出 :class:`OpenAPISchemaError`，错误信息含 ``A``、``B``。"""
        spec: dict[str, Any] = {
            "components": {
                "parameters": {
                    "A": {"$ref": "#/components/parameters/B"},
                    "B": {"$ref": "#/components/parameters/A"},
                }
            }
        }

        with pytest.raises(OpenAPISchemaError) as exc:
            validate_cycle_refs(spec)

        msg = str(exc.value)
        cycle_path = msg.removeprefix("Cycle detected in parameter $ref chain: ")
        parts = [part.strip() for part in cycle_path.split("->")]
        assert parts[0] == parts[-1]
        assert "A" in parts
        assert "B" in parts

    def test_validate_cycle_refs_no_cycle_returns_silently(self) -> None:
        """非环参数链（引用同一内联参数或只引用一次）静默通过不抛异常。"""
        spec: dict[str, Any] = {
            "components": {
                "parameters": {
                    "A": {
                        "name": "foo",
                        "in": "query",
                        "schema": {"type": "string"},
                    },
                    "B": {"$ref": "#/components/parameters/A"},
                }
            }
        }

        validate_cycle_refs(spec)
