"""参数（query / path / header）渲染相关的辅助函数。

- :func:`make_param_fields` — 参数信息 → 字段 :class:`FieldDecl` 列表。
- :func:`build_content_type_header` — 派生 Content-Type header field。
"""

from __future__ import annotations

from typing import Any

from stoma.openapi.fields import build_param_field_line
from stoma.openapi.models import FieldDecl
from stoma.openapi.naming import is_snake_case
from stoma.openapi.type_mapping import (
    is_nullable_json_type,
    python_type_for_nullable_param,
)


def make_param_fields(parameters: list[Any]) -> tuple[list[FieldDecl], list[FieldDecl], bool]:
    """将参数信息（query / header / path）转换为 :class:`FieldDecl` 列表。

    每个参数的 ``description`` / ``example`` / ``examples`` 会被提取并传入
    :func:`stoma.openapi.fields.build_param_field_line` 派生字段
    :class:`FieldDecl`，模板按 ``decl.line`` / ``decl.docstring`` 解包渲染。

    description / example 缺失时 ``docstring`` 为 ``None``，模板跳过空 docstring
    行渲染，与 dmcg 1:1 对齐。

    :param parameters: OpenAPI 参数列表。
    :return: ``(Header FieldDecl 列表, Query/Path FieldDecl 列表, uses_field_import)``。
        ``uses_field_import`` 为 ``True`` 时表示存在至少一个非 snake_case
        参数，其字段声明会引用 ``Field(serialization_alias=...)``，
        渲染时需要在模板里加上 ``from pydantic import Field`` 导入。
    :raise OpenAPISchemaError: 参数 schema 类型不支持时抛出，
        包括 str 非 primitive、list 含 3+ 元素、或含 "object" 等不支持的形态。
    """
    header_fields: list[FieldDecl] = []
    param_fields: list[FieldDecl] = []
    uses_field_import = False

    for param in parameters:
        name = param.name or ""
        param_in = param.param_in
        location = param_in.value if param_in else "query"
        required = param.required or False
        schema = param.param_schema

        # 参数级 ``$ref`` 已在 :func:`src.openapi.parser.make_openapi_parser`
        # 上游通过 :func:`src.openapi.reference.expand_path_refs` 展开为内联 schema，
        # 因此 ``schema`` 此时只会是普通 Schema（不会是 :attr:`EndpointRenderer.Reference`
        # 注入的 ``Reference30`` / ``Reference31`` 实例）。
        schema_dict = schema.model_dump(mode="json") if schema else {}
        json_type = schema_dict.get("type", "Any")
        items_dict = schema_dict.get("items")
        # 新逻辑：支持 OpenAPI 3.1 nullable list 语法（`type: ["<primitive>", "null"]`
        # / `type: ["array", "null"]`），通过 `python_type_for_nullable_param`
        # 内部校验，不支持的形态由该函数抛出 OpenAPISchemaError。
        param_type = python_type_for_nullable_param(json_type, items_dict)
        if is_nullable_json_type(json_type):
            param_type = f"{param_type} | None"

        if not is_snake_case(name):
            uses_field_import = True

        # 三态描述/示例：parameter 优先于 schema（OpenAPI spec 语义），
        # description/example/examples 都缺失时 ``docstring`` 为 ``None``。
        description = getattr(param, "description", None)
        if description is None:
            description = schema_dict.get("description")
        example = getattr(param, "example", None)
        examples = getattr(param, "examples", None)

        field_decl = build_param_field_line(
            name,
            param_type,
            required,
            location,
            description=description,
            example=example,
            examples=examples,
        )

        if location == "header":
            header_fields.append(field_decl)
        else:
            param_fields.append(field_decl)

    return header_fields, param_fields, uses_field_import


def build_content_type_header(
    header_fields: list[FieldDecl],
    media_type: str | None,
) -> str | None:
    """当 endpoint 无显式 ``Content-Type`` header 字段且 ``media_type`` 非空时，生成自动派生。

    渲染 ``content_type: Annotated[str, Header(), Field(serialization_alias="Content-Type")] = "<media_type>"``，
    保证运行时发送的 Content-Type 与 spec 一致。
    已有显式 ``Content-Type`` header 字段时返回 ``None``，避免冲突。

    :param header_fields: 已收集的 header 字段 :class:`FieldDecl` 列表（query/path
        阶段渲染后）。通过 ``.line`` 搜索 ``alias="Content-Type"`` 判重。
    :param media_type: body fields 子类的 ``media_type``，为 ``None`` 时
        不需要生成（JSON / urlencoded / multipart 由 Playwright 处理）。
    :return: 字段声明字符串，已存在显式 Content-Type 或 ``media_type`` 为空时返回 ``None``。
    """
    if media_type is None:
        return None
    if any('alias="Content-Type"' in decl.line for decl in header_fields):
        return None
    return f'content_type: Annotated[str, Header(), Field(serialization_alias="Content-Type")] = "{media_type}"'


__all__ = ["build_content_type_header", "make_param_fields"]
