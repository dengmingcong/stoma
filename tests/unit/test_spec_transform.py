"""测试 :mod:`src.openapi.spec_transform` 的三个纯函数。"""

from __future__ import annotations

from typing import Any

from src.openapi.models import Endpoint
from src.openapi.spec_transform import (
    EmbedInfo,
    inject_inline_titles,
    operation_id_to_pascal,
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


class TestOperationIdToPascal:
    """测试 :func:`operation_id_to_pascal` 处理多种命名格式。"""

    def test_camel_case(self) -> None:
        """camelCase：``createItem`` → ``CreateItem``。"""
        assert operation_id_to_pascal("createItem") == "CreateItem"

    def test_snake_case(self) -> None:
        """snake_case：``list_users`` → ``ListUsers``。"""
        assert operation_id_to_pascal("list_users") == "ListUsers"

    def test_pascal_case(self) -> None:
        """PascalCase：``ListItems`` → ``ListItems``。"""
        assert operation_id_to_pascal("ListItems") == "ListItems"

    def test_hyphen_separator(self) -> None:
        """连字符：``create-item`` → ``CreateItem``。"""
        assert operation_id_to_pascal("create-item") == "CreateItem"

    def test_empty_string(self) -> None:
        """空字符串返回空字符串。"""
        assert operation_id_to_pascal("") == ""

    def test_single_word(self) -> None:
        """单词：``create`` → ``Create``。"""
        assert operation_id_to_pascal("create") == "Create"


class TestInjectInlineTitles:
    """测试 :func:`inject_inline_titles` 给内联 object 注入 title。"""

    def test_injects_title_for_inline_request_body(self) -> None:
        """内联请求体 object 应被注入 ``<OperationId>Request``。"""
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
        new_spec = inject_inline_titles(spec, [endpoint])
        schema = new_spec["paths"]["/items"]["post"]["requestBody"]["content"]["application/json"]["schema"]
        assert schema["title"] == "CreateItemRequest"

    def test_injects_title_for_inline_response(self) -> None:
        """内联响应 object 应被注入 ``<OperationId>Response``。"""
        spec: dict[str, Any] = {
            "paths": {
                "/items": {
                    "get": {
                        "responses": {
                            "200": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {"id": {"type": "string"}},
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        endpoint = _make_endpoint("listItems", method="get", path="/items")
        new_spec = inject_inline_titles(spec, [endpoint])
        schema = new_spec["paths"]["/items"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
        assert schema["title"] == "ListItemsResponse"

    def test_injects_title_for_201_response(self) -> None:
        """201 响应也应该被识别。"""
        spec: dict[str, Any] = {
            "paths": {
                "/items": {
                    "post": {
                        "responses": {
                            "201": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {"id": {"type": "string"}},
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        endpoint = _make_endpoint("createItem", path="/items")
        new_spec = inject_inline_titles(spec, [endpoint])
        schema = new_spec["paths"]["/items"]["post"]["responses"]["201"]["content"]["application/json"]["schema"]
        assert schema["title"] == "CreateItemResponse"

    def test_skips_ref_schemas(self) -> None:
        """``$ref`` schema 不会被注入 title。"""
        spec: dict[str, Any] = {
            "paths": {
                "/users": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/User"}
                                }
                            }
                        }
                    }
                }
            }
        }
        endpoint = _make_endpoint("createUser", path="/users")
        new_spec = inject_inline_titles(spec, [endpoint])
        schema = new_spec["paths"]["/users"]["post"]["requestBody"]["content"]["application/json"]["schema"]
        assert "$ref" in schema
        assert "title" not in schema

    def test_skips_object_without_properties(self) -> None:
        """无 ``properties`` 的 object 不被注入 title。"""
        spec: dict[str, Any] = {
            "paths": {
                "/items": {
                    "post": {
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {"type": "object"}
                                }
                            }
                        }
                    }
                }
            }
        }
        endpoint = _make_endpoint("createItem", path="/items")
        new_spec = inject_inline_titles(spec, [endpoint])
        schema = new_spec["paths"]["/items"]["post"]["requestBody"]["content"]["application/json"]["schema"]
        assert "title" not in schema

    def test_does_not_mutate_input(self) -> None:
        """函数必须为纯函数，不修改入参。"""
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
        inject_inline_titles(spec, [endpoint])
        schema = spec["paths"]["/items"]["post"]["requestBody"]["content"]["application/json"]["schema"]
        assert "title" not in schema

    def test_empty_endpoints_is_noop(self) -> None:
        """空 endpoint 列表时返回 deep copy，不修改入参。"""
        spec: dict[str, Any] = {"paths": {"/x": {"post": {"responses": {}}}}}
        new_spec = inject_inline_titles(spec, [])
        assert new_spec == spec
        assert new_spec is not spec


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
                                        "properties": {
                                            "data": {"$ref": "#/components/schemas/User"}
                                        },
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
        assert embed_infos[0] == EmbedInfo(
            operation_id="createUser", field_name="data", model_name="User"
        )

    def test_unwraps_embed_with_inline_object(self) -> None:
        """``{data: {properties: ...}}`` 应被解包为内层 object。"""
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
            "properties": {"name": {"type": "string"}},
        }
        assert embed_infos[0].field_name == "data"

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
                                                "required": ["inner"],
                                                "properties": {
                                                    "inner": {"$ref": "#/components/schemas/Item"}
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
    """测试 :func:`transform_spec_for_generation` 组合两个步骤。"""

    def test_composes_title_injection_and_embed_unwrap(self) -> None:
        """组合：内联 wrapper 的内层应被注入 title，且 wrapper 被解开。"""
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
        assert len(embed_infos) == 1
        assert embed_infos[0].field_name == "data"
        assert embed_infos[0].model_name == "CreateItemRequest"
