"""Pydantic 字段声明字符串构造。

- :func:`resolve_array_type` — ``type: array`` 派生 ``list[<T>]`` 字符串。
- :func:`build_form_field_line` — form 标量字段声明（含 snake_case 边界处理）。
- :func:`build_upload_file_field_line` — multipart file 字段声明。
- :func:`build_param_field_line` — query / path / header 参数字段声明
  （8 种分支形态）。
"""

from __future__ import annotations

from typing import Any

from stoma.openapi.naming import is_snake_case, to_field_name
from stoma.openapi.type_mapping import python_type_for_array_items


def resolve_array_type(prop_schema: dict[str, Any]) -> str:
    """对 ``type: array`` 的 property 派生 ``list[<T>]`` 字符串。

    从 ``prop_schema["items"]`` 取元素信息，委托给
    :func:`src.openapi.type_mapping.python_type_for_array_items`。
    ``items`` 缺失或类型未命中映射时 fallback 到 ``"list[str]"``。

    :param prop_schema: property 的 schema 字典（含 ``type`` / ``items``）。
    :return: ``"list[<T>]"`` 形式的 Python 类型字符串。
    """
    items = prop_schema.get("items")
    return python_type_for_array_items(items)


def build_form_field_line(name: str, py_type: str) -> str:
    """构造 form 字段声明字符串，含非 snake_case 自动 ``Field(serialization_alias=...)``。

    字段名走 :func:`openapi.naming.to_field_name` 处理 hyphen / 关键字 /
    数字开头等边界；若转换结果与原名不同（非合法 snake_case），追加
    ``Field(serialization_alias=<原名!r>)`` 让 FastAPI Form 提交时用原名，
    避免接口协议破坏（参考 :func:`build_param_field_line` 的非 snake_case 分支）。

    :param name: 原始 OpenAPI property 名称。
    :param py_type: Python 类型字符串。
    :return: 字段声明字符串。
    """
    field_name = to_field_name(name)
    if not is_snake_case(name):
        return f"{field_name}: Annotated[{py_type}, Form(), Field(serialization_alias={name!r})]"
    return f"{field_name}: Annotated[{py_type}, Form()]"


def build_upload_file_field_line(name: str) -> str:
    """构造 multipart file 字段声明字符串。

    ``name`` 非 snake_case 时追加 ``Field(serialization_alias=<origin>)``
    （与 form 标量字段一致——FastAPI Form / Playwright FormData 提交时用原名，
    避免接口协议破坏）。``name`` 已是 snake_case 时裸 ``UploadFile``。

    字段名同样走 :func:`openapi.naming.to_field_name` 处理边界
    （hyphen / 关键字 / 数字开头等）。

    :param name: 原始 OpenAPI property 名称。
    :return: 字段声明字符串（snake_case 时裸 ``UploadFile``，非 snake_case 时带 alias）。
    """
    field_name = to_field_name(name)
    if is_snake_case(name):
        return f"{field_name}: UploadFile"
    return f"{field_name}: Annotated[UploadFile, Field(serialization_alias={name!r})]"


def build_param_field_line(
    name: str,
    param_type: str,
    required: bool,
    location: str,
) -> str:
    """构建参数（query / path / header）字段声明字符串。

    使用 FastAPI 推荐的 ``Annotated[...]`` 形式：所有 metadata
    （``Header()`` / ``Field(serialization_alias=...)``）放进
    ``Annotated[...]`` 内，只在可选字段上保留 ``= None`` 默认值。

    八种分支形态：

    - header × required × snake: ``name: Annotated[T, Header()]``
    - header × required × non-snake:
      ``name: Annotated[T, Header(), Field(serialization_alias='X')]``
    - header × optional × snake:
      ``name: Annotated[T | None, Header()] = None``
    - header × optional × non-snake:
      ``name: Annotated[T | None, Header(), Field(serialization_alias='X')] = None``
    - query/path × required × snake: ``name: T``
    - query/path × required × non-snake:
      ``name: Annotated[T, Field(serialization_alias='X')]``
    - query/path × optional × snake: ``name: T | None = None``
    - query/path × optional × non-snake:
      ``name: Annotated[T | None, Field(serialization_alias='X')] = None``

    :param name: 原始 OpenAPI 参数名。
    :param param_type: Python 类型字符串。
    :param required: 是否必需。
    :param location: ``"header"`` / ``"query"`` / ``"path"``。
    :return: 字段声明字符串。
    """
    is_header = location == "header"
    is_snake = is_snake_case(name)
    field_name = name if is_snake else to_field_name(name)

    if required:
        base_type = param_type
    elif " | None" in param_type:
        base_type = param_type
    else:
        base_type = f"{param_type} | None"

    metadata: list[str] = []
    if is_header:
        metadata.append("Header()")
    if not is_snake:
        metadata.append(f"Field(serialization_alias={name!r})")

    if metadata:
        annotation = f"Annotated[{base_type}, {', '.join(metadata)}]"
    else:
        annotation = base_type

    default = "" if required else " = None"
    return f"{field_name}: {annotation}{default}"


__all__ = [
    "build_form_field_line",
    "build_param_field_line",
    "build_upload_file_field_line",
    "resolve_array_type",
]
