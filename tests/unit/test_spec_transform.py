"""测试 :mod:`src.openapi.spec_transform` 的解包与组合函数。

历史注记：原 ``inject_inline_titles`` 已合并到 :mod:`src.openapi.parser`
的 ``_fill_schema_titles``（在 prance 之前一次性注入所有 title），
所以本模块只测 :func:`unwrap_embed_wrappers` 和 :func:`transform_spec_for_generation`。
"""

from __future__ import annotations

from typing import Any

from src.openapi.models import Endpoint
from src.openapi.spec_transform import (
    EmbedInfo,
    transform_spec_for_generation,
    unwrap_embed_wrappers,
)


def _make_endpoint(
    operation_id: str,
    method: str = "post",
    path: str = "/items",
) -> Endpoint:
    """构造一个最小可用的 :class:`Endpoint` 用于测试。"""
    return Endpoint(
        operation_id=operation_id,
        method=method,
        path=path,
        summary=None,
        description=None,
        parameters=[],
        request_body=None,
        responses=None,
    )


class TestUnwrapEmbedWrappers:
    """测试 :func:`unwrap_embed_wrappers` 解包单属性 wrapper。"""

    def test_unwraps_simple_embed_with_ref(self) -> None:
        """``{data: $ref User}`` 应被解包为 ``$ref User``。"""
        spec: dict[str, Any] = {
            "paths": {
                "/users": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["data"],
                                        "properties": {"data": {"$ref": "#/components/schemas/User"}},
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        endpoint = _make_endpoint("createUser", path="/users")
        new_spec, embed_infos = unwrap_embed_wrappers(spec, [endpoint])
        schema = new_spec["paths"]["/users"]["post"]["requestBody"]["content"]["application/json"]["schema"]
        assert schema == {"$ref": "#/components/schemas/User"}
        assert len(embed_infos) == 1
        assert embed_infos[0] == EmbedInfo(operation_id="createUser", field_name="data", model_name="User")

    def test_unwraps_embed_with_inline_object(self) -> None:
        """``{data: {properties: ...}}`` 应被解包为内层 object。

        title 已经在 parser 阶段的 ``_fill_schema_titles`` 里被注入到内层
        （pre-process 穿透 embed wrapper 处理），所以解包后内层带 title。
        """
        spec: dict[str, Any] = {
            "paths": {
                "/items": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["data"],
                                        "properties": {
                                            "data": {
                                                "type": "object",
                                                "title": "CreateItemRequest",
                                                "properties": {"name": {"type": "string"}},
                                            }
                                        },
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        endpoint = _make_endpoint("createItem", path="/items")
        new_spec, embed_infos = unwrap_embed_wrappers(spec, [endpoint])
        schema = new_spec["paths"]["/items"]["post"]["requestBody"]["content"]["application/json"]["schema"]
        assert schema == {
            "type": "object",
            "title": "CreateItemRequest",
            "properties": {"name": {"type": "string"}},
        }
        assert embed_infos[0].field_name == "data"
        assert embed_infos[0].model_name == "CreateItemRequest"

    def test_unwraps_nested_embed(self) -> None:
        """嵌套 embed 多层应递归解包到最内层。"""
        spec: dict[str, Any] = {
            "paths": {
                "/items": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["outer"],
                                        "properties": {
                                            "outer": {
                                                "type": "object",
                                                "title": "Item",
                                                "required": ["inner"],
                                                "properties": {
                                                    "inner": {"$ref": "#/components/schemas/Item"},
                                                },
                                            }
                                        },
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        endpoint = _make_endpoint("createItem", path="/items")
        new_spec, embed_infos = unwrap_embed_wrappers(spec, [endpoint])
        schema = new_spec["paths"]["/items"]["post"]["requestBody"]["content"]["application/json"]["schema"]
        assert schema == {"$ref": "#/components/schemas/Item"}
        # 只记录最外层 wrapper
        assert embed_infos[0].field_name == "outer"
        assert embed_infos[0].model_name == "Item"

    def test_skips_single_property_not_required(self) -> None:
        """单 property 但不在 required → 不解包。"""
        spec: dict[str, Any] = {
            "paths": {
                "/items": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {"name": {"type": "string"}},
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        endpoint = _make_endpoint("createItem", path="/items")
        new_spec, embed_infos = unwrap_embed_wrappers(spec, [endpoint])
        assert new_spec == spec
        assert embed_infos == []

    def test_skips_multiple_properties(self) -> None:
        """多 property 的 object → 不解包。"""
        spec: dict[str, Any] = {
            "paths": {
                "/items": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["a", "b"],
                                        "properties": {
                                            "a": {"type": "string"},
                                            "b": {"type": "string"},
                                        },
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        endpoint = _make_endpoint("createItem", path="/items")
        new_spec, embed_infos = unwrap_embed_wrappers(spec, [endpoint])
        assert new_spec == spec
        assert embed_infos == []

    def test_skips_non_object_schema(self) -> None:
        """非 object 的 schema 不解包。"""
        spec: dict[str, Any] = {
            "paths": {
                "/items": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {"type": "string"}
                                }
                            }
                        }
                    }
                }
            }
        }
        endpoint = _make_endpoint("createItem", path="/items")
        new_spec, embed_infos = unwrap_embed_wrappers(spec, [endpoint])
        assert new_spec == spec
        assert embed_infos == []


class TestTransformSpecForGeneration:
    """测试 :func:`transform_spec_for_generation` 组合步骤。"""

    def test_unwraps_embed_with_ref(self) -> None:
        """组合：``{data: $ref User}`` 解包后内层是 $ref User。"""
        spec: dict[str, Any] = {
            "paths": {
                "/users": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["data"],
                                        "properties": {"data": {"$ref": "#/components/schemas/User"}},
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        endpoint = _make_endpoint("createUser", path="/users")
        new_spec, embed_infos = transform_spec_for_generation(spec, [endpoint])
        schema = new_spec["paths"]["/users"]["post"]["requestBody"]["content"]["application/json"]["schema"]
        assert schema == {"$ref": "#/components/schemas/User"}
        assert len(embed_infos) == 1
        assert embed_infos[0].field_name == "data"
        assert embed_infos[0].model_name == "User"

    def test_unwraps_embed_with_titled_inner(self) -> None:
        """组合：title 已在 parser 阶段注入到内层，unwrap 后保留。"""
        spec: dict[str, Any] = {
            "paths": {
                "/items": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["data"],
                                        "properties": {
                                            "data": {
                                                "type": "object",
                                                "title": "CreateItemRequest",
                                                "properties": {"name": {"type": "string"}},
                                            }
                                        },
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        endpoint = _make_endpoint("createItem", path="/items")
        new_spec, embed_infos = transform_spec_for_generation(spec, [endpoint])
        schema = new_spec["paths"]["/items"]["post"]["requestBody"]["content"]["application/json"]["schema"]
        assert schema["title"] == "CreateItemRequest"
        assert embed_infos[0].field_name == "data"
        assert embed_infos[0].model_name == "CreateItemRequest"
