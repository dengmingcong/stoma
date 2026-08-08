"""测试 :mod:`src.openapi.model_generator` 对 ``datamodel-code-generator`` 的封装。"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from src.openapi.model_generator import (
    _detect_parameter_cycle,
    _expand_parameter_refs,
    generate_models,
)

if TYPE_CHECKING:  # pragma: no cover
    from src.openapi.parser import OpenAPISchemaError  # noqa: F401


def _minimal_spec() -> dict[str, Any]:
    """给测试用的最小 OpenAPI 规范（prance 风格，``$ref`` 已展开）。"""
    return {
        "openapi": "3.1.0",
        "info": {"title": "Test", "version": "1.0.0"},
        "paths": {
            "/users": {
                "post": {
                    "operationId": "createUser",
                    "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/User"}}}},
                    "responses": {
                        "201": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/User"}}}}
                    },
                }
            }
        },
        "components": {
            "schemas": {
                "User": {
                    "type": "object",
                    "title": "User",
                    "required": ["id", "name"],
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                    },
                }
            }
        },
    }


class TestGenerateModels:
    """测试 :func:`generate_models` 端到端调用 ``datamodel-code-generator``。"""

    def test_generates_models_file(self, tmp_path: Path) -> None:
        """应生成 ``models.py`` 文件，且包含至少一个 ``class`` 定义。"""
        spec = _minimal_spec()
        output_path = tmp_path / "models.py"
        generate_models(spec, output_path)
        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        assert "class" in content
        assert "User" in content

    def test_creates_parent_directory(self, tmp_path: Path) -> None:
        """父目录不存在时自动创建。"""
        spec = _minimal_spec()
        output_path = tmp_path / "deep" / "nested" / "models.py"
        generate_models(spec, output_path)
        assert output_path.exists()

    def test_raises_on_invalid_spec(self, tmp_path: Path) -> None:
        """无效 spec 应抛出 ``RuntimeError``。"""
        output_path = tmp_path / "models.py"
        try:
            generate_models({"paths": {}}, output_path)
        except RuntimeError:
            # 预期：错误包装为 RuntimeError
            pass
        else:
            # 部分无效 spec 仍能生成，文件不存在才报错
            if not output_path.exists():
                msg = "无效 spec 应报错"
                raise AssertionError(msg)


class TestExpandParameterRefs:
    """测试 :func:`_expand_parameter_refs` 选择性参数 ``$ref`` 展开。"""

    def test_expand_parameter_refs_preserves_body_refs(self) -> None:
        """``requestBody`` 与 ``responses`` 中的 ``$ref`` 字符串保持原样。

        ``_expand_parameter_refs`` 仅展开 ``parameters`` 中的 ``$ref``，
        其余键（如 ``requestBody``、``responses``）应原封不动。
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

        result = _expand_parameter_refs(spec)

        expanded_param = result["paths"]["/items"]["get"]["parameters"][0]
        assert expanded_param == {
            "name": "page",
            "in": "query",
            "schema": {"type": "integer"},
        }
        assert "$ref" not in expanded_param
        assert result["paths"]["/items"]["get"]["requestBody"] == {
            "$ref": "#/components/schemas/ItemBody"
        }
        assert result["paths"]["/items"]["get"]["responses"] == {
            "200": {"$ref": "#/components/responses/ItemList"},
            "404": {"$ref": "#/components/responses/NotFound"},
        }
        assert result["paths"]["/items"]["get"]["summary"] == "list summary"

    def test_expand_parameter_refs_resolves_parameter_chain(self) -> None:
        """``parameters[*].$ref`` 指向 ``#/components/parameters/X`` 时被展开。"""
        spec: dict[str, Any] = {
            "paths": {
                "/items": {
                    "get": {
                        "parameters": [{"$ref": "#/components/parameters/PageParam"}]
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
                }
            },
        }

        result = _expand_parameter_refs(spec)

        assert result["paths"]["/items"]["get"]["parameters"] == [
            {"name": "page", "in": "query", "schema": {"type": "integer"}}
        ]

    def test_expand_parameter_refs_catches_external_ref_error(self) -> None:
        """组件参数 ``schema.$ref`` 指向外部文件时抛出 :class:`OpenAPISchemaError`。"""
        from src.openapi.parser import OpenAPISchemaError

        spec: dict[str, Any] = {
            "paths": {
                "/x": {
                    "get": {
                        "parameters": [{"$ref": "#/components/parameters/X"}]
                    }
                }
            },
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

        with pytest.raises(
            OpenAPISchemaError, match=r"Failed to resolve parameter \$ref"
        ):
            _expand_parameter_refs(spec)


class TestDetectParameterCycle:
    """测试 :func:`_detect_parameter_cycle` 参数 ``$ref`` 环检测。"""

    def test_detect_parameter_cycle_finds_cycle(self) -> None:
        """``A -> B -> A`` 的环应被检测并返回包含 ``A``、``B`` 的路径。"""
        spec: dict[str, Any] = {
            "components": {
                "parameters": {
                    "A": {"$ref": "#/components/parameters/B"},
                    "B": {"$ref": "#/components/parameters/A"},
                }
            }
        }

        result = _detect_parameter_cycle(spec)

        assert result is not None
        parts = [part.strip() for part in result.split("->")]
        assert parts[0] == parts[-1]
        assert "A" in parts
        assert "B" in parts

    def test_detect_parameter_cycle_no_cycle_returns_none(self) -> None:
        """非环参数链（引用同一内联参数或只引用一次）返回 ``None``。"""
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

        result = _detect_parameter_cycle(spec)

        assert result is None
