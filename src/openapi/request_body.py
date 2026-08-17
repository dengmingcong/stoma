"""请求体渲染相关的辅助函数。

- :func:`flatten_body_fields` — body fields 子类拍平为 template 变量字典。
- :func:`is_body_fields_use_field` — 判断 body 字段声明是否含 ``Field(``。
- :func:`get_media_type_schema` — 取指定 media_type 的原始 schema Pydantic 模型。
- :func:`get_expanded_schema_dict` — 取指定 media_type 的 schema 并用 jsonref 展开。
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from src.openapi.models import (
    BinaryRequestBodyFields,
    JSONRequestBodyFields,
    MultipartFormRequestBodyFields,
    RequestBodyFields,
    ScalarRequestBodyFields,
    UrlencodedFormRequestBodyFields,
)


def flatten_body_fields(body_fields: RequestBodyFields | None) -> dict[str, Any]:
    """把 body fields 子类拍平为 template 变量字典。

    NONE 路径返回空字典（所有 body 块条件不成立，自动跳过）。

    ``media_type`` 字段仅在 binary / scalar 子类有值，供
    :func:`src.openapi.parameters.build_content_type_header` 派生 Content-Type
    header；JSON / urlencoded / multipart 均为 ``None``，Playwright 自动处理
    Content-Type。

    :param body_fields: body 渲染字段（NONE 路径为 ``None``）。
    :return: 模板可直接 ``**vars`` 展开的字典（key 名对齐
        ``endpoint.py.jinja2`` 的变量名）。
    :raise TypeError: ``body_fields`` 不是已知的 body fields 子类类型。
    """
    if body_fields is None:
        return {
            "import_model": None,
            "scalar_field": None,
            "form_text_fields": [],
            "form_file_fields": [],
            "binary_file_field": None,
            "upload_as_multipart": True,
            "media_type": None,
        }
    if isinstance(body_fields, JSONRequestBodyFields):
        return {
            "import_model": body_fields.import_model,
            "scalar_field": None,
            "form_text_fields": [],
            "form_file_fields": [],
            "binary_file_field": None,
            "upload_as_multipart": True,
            "media_type": None,
        }
    if isinstance(body_fields, UrlencodedFormRequestBodyFields):
        return {
            "import_model": None,
            "scalar_field": None,
            "form_text_fields": body_fields.form_text_fields,
            "form_file_fields": [],
            "binary_file_field": None,
            "upload_as_multipart": True,
            "media_type": None,
        }
    if isinstance(body_fields, MultipartFormRequestBodyFields):
        return {
            "import_model": None,
            "scalar_field": None,
            "form_text_fields": body_fields.form_text_fields,
            "form_file_fields": body_fields.form_file_fields,
            "binary_file_field": None,
            "upload_as_multipart": True,
            "media_type": None,
        }
    if isinstance(body_fields, BinaryRequestBodyFields):
        return {
            "import_model": None,
            "scalar_field": None,
            "form_text_fields": [],
            "form_file_fields": [],
            "binary_file_field": body_fields.binary_file_field,
            "upload_as_multipart": False,
            "media_type": body_fields.media_type,
        }
    if isinstance(body_fields, ScalarRequestBodyFields):
        return {
            "import_model": None,
            "scalar_field": body_fields.scalar_field,
            "form_text_fields": [],
            "form_file_fields": [],
            "binary_file_field": None,
            "upload_as_multipart": True,
            "media_type": None,
        }
    msg = f"Unsupported body_fields type: {type(body_fields).__name__}"
    raise TypeError(msg)


def is_body_fields_use_field(body_template_vars: dict[str, Any]) -> bool:
    """判断 body 字段声明中是否含 ``Field(``，决定是否追加 ``from pydantic import Field``。

    4 类 body 字段（``form_text_fields`` / ``form_file_fields`` /
    ``binary_file_field`` / ``scalar_field``）的非 snake_case 形式都会
    包含 ``Field(serialization_alias=...)``。template 只看
    ``uses_field_import`` 决定是否加 import，所以 body-only Field 用法
    需要在 render 阶段显式翻起该标志。

    :param body_template_vars: :func:`flatten_body_fields` 输出的字典。
    :return: 任意 body 字段含 ``Field(`` 子串时返回 ``True``。
    """
    for key in ("form_text_fields", "form_file_fields"):
        for line in body_template_vars.get(key, []):
            if "Field(" in line:
                return True
    for key in ("binary_file_field", "scalar_field"):
        value = body_template_vars.get(key)
        if isinstance(value, str) and "Field(" in value:
            return True
    return False


def get_media_type_schema(
    request_body: Any,
    media_type: str,
) -> BaseModel | None:
    """从 ``request_body.content`` 取指定 ``media_type`` 的原始 schema Pydantic 模型。

    与 :func:`get_expanded_schema_dict` 的区别：本函数返回原始 Pydantic 模型
    （``Reference30`` / ``Reference31`` / ``Schema30`` / ``Schema31``），供
    ``EndpointRenderer._build_json_body`` 直接用 ``isinstance(schema, Reference)``
    检测 Reference 并访问 ``schema.ref`` 派生 model 名——jsonref 展开后会丢失
    ``$ref`` 信息，必须回到原始模型才能拿到。

    非 JSON 路径仍走 :func:`get_expanded_schema_dict`（需要遍历 properties）。

    :param request_body: openapi-pydantic ``RequestBody`` 实例。
    :param media_type: 媒体类型字符串（如 ``"application/json"``）。
    :return: 原始 ``media_type_schema`` Pydantic 模型，缺失时返回 ``None``。
    """
    content = getattr(request_body, "content", None)
    if not isinstance(content, dict):
        return None
    media_type_obj = content.get(media_type)
    if media_type_obj is None:
        return None
    return getattr(media_type_obj, "media_type_schema", None)


__all__ = [
    "flatten_body_fields",
    "get_media_type_schema",
    "is_body_fields_use_field",
]
