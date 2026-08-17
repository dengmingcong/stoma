"""JSON Schema ``type`` 字符串与 Python 类型之间的映射关系。

集中存放：

- :data:`JSON_PRIMITIVE_TYPES`：OpenAPI scalar / form / parameter 路径支持的
  primitive 类型集合（``string`` / ``integer`` / ``number`` / ``boolean``），
  取代代码里硬编码的 ``{"string", "integer", "number", "boolean"}`` 字面量。
- :data:`JSON_TYPE_TO_PYTHON`：完整 JSON Schema ``type`` → Python 类型名的映射
  （含 ``array`` / ``object`` / ``null`` 的简单映射）。
- :func:`is_primitive_json_type` / :func:`python_type_name` /
  :func:`python_type_for_array_items`：派生 Python 类型名的辅助函数，
  供 renderer 把 OpenAPI schema 字符串映射为 Pydantic 字段声明中可写的
  Python 类型表达式。
"""

from __future__ import annotations

from typing import Any

from stoma.exceptions import OpenAPISchemaError

# OpenAPI scalar / form / parameter 路径支持的 primitive 类型集合。
# 顶层 body 通常走 ``$ref``，仅这 4 个 primitive 类型可作为裸 scalar。
JSON_PRIMITIVE_TYPES: frozenset[str] = frozenset({"string", "integer", "number", "boolean"})

# JSON Schema ``type`` 字符串 → Python 类型名字符串映射。
# 含 OpenAPI scalar / form / parameter 路径支持的 4 个 primitive 类型，
# 以及 ``array`` / ``object`` / ``null`` 的简单映射。``array`` 元素的
# 展开见 :func:`python_type_for_array_items`。
JSON_TYPE_TO_PYTHON: dict[str, str] = {
    "string": "str",
    "integer": "int",
    "number": "float",
    "boolean": "bool",
    "array": "list",
    "object": "dict",
    "null": "None",
}


def is_primitive_json_type(json_type: object) -> bool:
    """判断是否为 OpenAPI scalar / form / parameter 路径支持的 primitive 类型。

    取代代码里硬编码的 ``{"string", "integer", "number", "boolean"}`` 集合，
    由 :data:`JSON_PRIMITIVE_TYPES` 作为单一来源。

    :param json_type: 待判断的 JSON Schema ``type`` 值（可能为 ``None`` 或非 str）。
    :return: 命中 :data:`JSON_PRIMITIVE_TYPES` 时返回 ``True``。
    """
    return isinstance(json_type, str) and json_type in JSON_PRIMITIVE_TYPES


def python_type_name(json_type: str) -> str:
    """JSON Schema ``type`` 字符串 → Python 类型名字符串。

    :param json_type: JSON Schema ``type`` 字符串。
    :return: 命中 :data:`JSON_TYPE_TO_PYTHON` 时返回对应 Python 类型名；
        未命中时返回原字符串（用于 ``cast`` / debug 时保留原信息）。
    """
    return JSON_TYPE_TO_PYTHON.get(json_type, json_type)


def python_type_for_array_items(items: dict[str, Any] | None) -> str:
    """对 ``type: array`` 的 property 派生 ``list[<T>]`` 字符串。

    从 ``items["type"]`` 取元素类型映射到 Python 类型名；
    ``items`` 缺失或类型未命中 :data:`JSON_TYPE_TO_PYTHON` 时 fallback 到
    ``"list[str]"``（与原 ``_resolve_array_type`` 行为一致——form / scalar
    body 场景不暴露 array 解析失败，转用宽松兜底）。

    :param items: array schema 的 ``items`` 字典，可能为 ``None`` 或非 dict。
    :return: ``"list[<T>]"`` 形式的 Python 类型字符串。
    """
    if not isinstance(items, dict):
        return "list[str]"
    return f"list[{python_type_name(items.get('type', '') or 'str')}]"


def is_nullable_json_type(json_type: object) -> bool:
    """判断 JSON Schema ``type`` 值是否为 OpenAPI 3.1 nullable list 语法。

    OpenAPI 3.1 支持以列表形式声明可空类型，例如 ``["string", "null"]``
    或 ``["array", "null"]``。本函数判断传入的 ``json_type`` 是否属于此类
    nullable list。

    :param json_type: JSON Schema ``type`` 值，可能为 str、list、None 或其他类型。
    :return: 当 ``json_type`` 为 list 且含 ``"null"`` 时返回 ``True``，
        否则返回 ``False``。
    """
    return isinstance(json_type, list) and "null" in json_type


def extract_non_null_type(json_type: list[str]) -> str:
    """从 nullable list 中提取非 null 的那个类型字符串。

    假设 list 最多 2 元素，必有一个非 null。常见形态为 ``["string", "null"]``
    或 ``["array", "null"]``。

    :param json_type: 包含 null 的 JSON Schema type 列表。
    :return: 非 null 的那个类型字符串。
    :raise OpenAPISchemaError: list 中找不到非 null 元素时抛出。
    """
    for t in json_type:
        if t != "null":
            return t
    msg = f"Nullable list must contain at least one non-null type: {json_type!r}"
    raise OpenAPISchemaError(msg)


def python_type_for_nullable_param(json_type: object, items: dict[str, Any] | None) -> str:
    """为 OpenAPI 3.1 nullable parameter schema 派生 Python 类型名字符串。

    处理三种形态：

    1. ``json_type`` 为 str 且在 :data:`JSON_PRIMITIVE_TYPES` 中：
       直接查 :data:`JSON_TYPE_TO_PYTHON` 返回。
    2. ``json_type`` 为 list 且仅含 ``"null"`` + 一个 primitive：
       提取该 primitive，调用 :func:`python_type_name` 返回。
    3. ``json_type`` 为 list 且含 ``"null"`` + ``"array"``：
       用 ``items`` 调用 :func:`python_type_for_array_items` 派生元素类型，
       包成 ``f"list[{element_type}]"``。

    :param json_type: JSON Schema ``type`` 值，可能为 str 或 list。
    :param items: 当 ``json_type`` 含 ``"array"`` 时的 items schema 字典。
    :return: Python 类型名字符串（如 ``"str"``、``"int"``、``"list[str]"``）。
    :raise OpenAPISchemaError: 遇到不支持的形态时抛出，
        包括 ``["object", "null"]``、list 含 3+ 元素、str 形态非 primitive。
    """
    if isinstance(json_type, str):
        if json_type in JSON_PRIMITIVE_TYPES:
            return JSON_TYPE_TO_PYTHON[json_type]
        msg = f"Unsupported nullable param schema: {json_type!r}"
        raise OpenAPISchemaError(msg)

    if isinstance(json_type, list):
        if len(json_type) > 2:
            msg = f"Unsupported nullable param schema: {json_type!r}"
            raise OpenAPISchemaError(msg)
        if "array" in json_type and "null" in json_type:
            return python_type_for_array_items(items)
        if "object" in json_type and "null" in json_type:
            msg = f"Unsupported nullable param schema: {json_type!r}"
            raise OpenAPISchemaError(msg)
        non_null = extract_non_null_type(json_type)
        return python_type_name(non_null)

    msg = f"Unsupported nullable param schema: {json_type!r}"
    raise OpenAPISchemaError(msg)


__all__ = [
    "JSON_PRIMITIVE_TYPES",
    "JSON_TYPE_TO_PYTHON",
    "is_primitive_json_type",
    "python_type_name",
    "python_type_for_array_items",
    "is_nullable_json_type",
    "extract_non_null_type",
    "python_type_for_nullable_param",
]
