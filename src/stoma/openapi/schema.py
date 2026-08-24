"""OpenAPI / JSON Schema 字典形态判定。"""

from __future__ import annotations

from typing import Any

from stoma.openapi.type_mapping import is_primitive_json_type


def has_combinator(schema: dict[str, Any] | None) -> bool:
    """检查 schema 是否含非空顶层 ``oneOf`` / ``anyOf`` / ``allOf`` key。

    multipart / urlencoded form 不支持顶层复合 key（renderer 无法静态推断
    fields）；JSON 路径也已显式拒绝（dmcg 处理 inline union 时需要
    ``$ref`` + inline merge 配合，原始 inline union 不再支持）。

    openapi-pydantic v3 的 ``Schema.model_dump(mode="json")`` 会把未设置的
    ``oneOf`` / ``anyOf`` / ``allOf`` 输出为显式 ``None`` key，因此判重时
    必须同时检查值非 ``None``。

    :param schema: 展开后的 schema 字典（可能为 ``None``）。
    :return: 命中任一非空复合 key 时返回 ``True``。
    """
    if not isinstance(schema, dict):
        return False
    return any(schema.get(key) is not None for key in ("oneOf", "anyOf", "allOf"))


def is_primitive_schema_dict(schema: dict[str, Any] | None) -> bool:
    """判断 schema 是否为 primitive（string / integer / number / boolean）。

    通过 :func:`src.openapi.type_mapping.is_primitive_json_type` 判定，
    取代硬编码的 ``{"string", "integer", "number", "boolean"}`` 集合。

    :param schema: 展开后的 schema 字典（可能为 ``None``）。
    :return: ``type`` 字段命中 primitive 类型集合时返回 ``True``。
    """
    if not isinstance(schema, dict):
        return False
    return is_primitive_json_type(schema.get("type"))


def is_binary_schema_dict(schema: dict[str, Any] | None) -> bool:
    """判断 schema 是否为 ``string + format=binary``（binary raw body）。

    兼容 openapi-pydantic v3 的 ``schema_format`` 双 key 兜底。

    :param schema: 展开后的 schema 字典（可能为 ``None``）。
    :return: ``type == "string"`` 且 ``format == "binary"`` 时返回 ``True``。
    """
    if not isinstance(schema, dict):
        return False
    if schema.get("type") != "string":
        return False
    schema_format: str = schema.get("schema_format", "") or schema.get("format", "")
    return schema_format == "binary"


__all__ = ["has_combinator", "is_binary_schema_dict", "is_primitive_schema_dict"]
