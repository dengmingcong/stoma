"""OpenAPI 生成器的中间表示（IR）模型。

本模块定义 ``Endpoint`` —— 表示单个 OpenAPI 接口（路径 + 方法 + 参数 +
请求体 + 响应）的不可变快照，供代码生成阶段使用。

通用化设计
==========

``Endpoint`` 是泛型类，三个类型参数 ``ParameterT``、``RequestBodyT``、
``ResponseT`` 都约束为 :class:`pydantic.BaseModel` 的子类。Parser 加载
完原始 spec 后，会按 spec 版本（``3.0`` / ``3.1``）选择具体类型参数：

- 3.0 → ``Endpoint[Parameter30, RequestBody30, Response30]``
- 3.1 → ``Endpoint[Parameter31, RequestBody31, Response31]``
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

from stoma.openapi.version import SpecVersion

__all__ = [
    "Endpoint",
    "FieldDecl",
    "JSONRequestBodyFields",
    "UrlencodedFormRequestBodyFields",
    "MultipartFormRequestBodyFields",
    "BinaryRequestBodyFields",
    "ScalarRequestBodyFields",
    "RequestBodyFields",
]


@dataclass(frozen=True)
class FieldDecl:
    """单一字段的渲染产物（``line`` + 字段 docstring）。

    ``line`` 是字段声明字符串（含 ``Annotated[...]`` / 默认值等），模板按
    原样写入；``docstring`` 非 ``None`` 时模板在 ``line`` 下一行追加字段
    docstring（``\"\"\"...\"\"\"`` 或 ``\"\"\"\\n...\\n\"\"\"``）。没有
    description / example 时 ``docstring`` 为 ``None``，模板跳过。

    docstring 文本由 :func:`stoma.openapi.fields.build_field_value`
    拼接（1:1 复刻 dmcg 0.72.2 ``model/base.py:887-921`` ``docstring``
    property），格式由 :func:`stoma.openapi.fields.build_field_docstring`
    套上三引号（1:1 复刻 dmcg ``model/base.py:181-214`` ``format_docstring``）。

    :var line: 字段声明字符串（不含末尾换行）。
    :vartype line: str
    :var docstring: 字段 docstring 完整字符串（含三引号）；无 description
        和 example 时为 ``None``，模板条件跳过。
    :vartype docstring: str | None
    """

    line: str
    docstring: str | None = None


# 5 种 body 形态对应的 dataclass 子类联合，供 renderer 类型签名简化。
type RequestBodyFields = (
    JSONRequestBodyFields
    | UrlencodedFormRequestBodyFields
    | MultipartFormRequestBodyFields
    | BinaryRequestBodyFields
    | ScalarRequestBodyFields
)


@dataclass
class JSONRequestBodyFields:
    """``application/json`` + object schema（``$ref`` 或 inline）。

    渲染为 ``from .models import <Model>`` + ``body: <Model>``。
    inline 形态由 dmcg 在前置阶段生成对应 ``{OpId}Request`` 模型。

    Content-Type 由 Playwright 根据 body 格式自动派生（JSON），renderer 不注入。

    :var import_model: 单一 model 名（``$ref`` 末段 PascalCase，或 inline 的 ``{op_id}Request``）。
    """

    import_model: str | None = None


@dataclass
class UrlencodedFormRequestBodyFields:
    """``application/x-www-form-urlencoded`` → form 标量字段列表。

    渲染为 ``from stoma import Form`` + 循环
    ``<name>: Annotated[<type>, Form()]`` 字段声明。

    Content-Type 由 Playwright 根据 ``form`` 参数自动派生（urlencoded），
    renderer 不注入。

    :var form_text_fields: form 标量字段 :class:`FieldDecl` 列表，
        由 :func:`stoma.openapi.fields.build_form_field_line` 派生，
        ``docstring`` 非 ``None`` 时模板在 ``line`` 下一行追加字段 docstring。
    """

    form_text_fields: list[FieldDecl] = field(default_factory=list)


@dataclass
class MultipartFormRequestBodyFields:
    """``multipart/form-data`` → form 标量 + 文件字段列表。

    Content-Type（含 boundary）由 Playwright 根据 ``multipart`` 参数自动派生，
    renderer 不注入——若用户显式提供 ``content_type`` Header field，stoma 不干预，
    由 Playwright 自行处理。

    :var form_text_fields: form 标量字段 :class:`FieldDecl` 列表。
    :var form_file_fields: file 字段 :class:`FieldDecl` 列表（裸 ``UploadFile``，
        无 ``Form()`` marker）；由 :func:`stoma.openapi.fields.build_upload_file_field_line`
        派生。
    """

    form_text_fields: list[FieldDecl] = field(default_factory=list)
    form_file_fields: list[FieldDecl] = field(default_factory=list)


@dataclass
class BinaryRequestBodyFields:
    """``string + format=binary`` → 单文件 raw body。

    ``upload_as_multipart=False`` 由类型本身表达，不需要额外字段。
    渲染为 ``body: UploadFile`` + decorator ``upload_as_multipart=False``。

    Binary body 没有隐含的 Content-Type（Playwright 无法从裸字节推断），renderer 必须
    显式生成 ``content_type: Header() = <media_type>`` header field。

    :var media_type: 媒体类型字符串（如 ``"application/octet-stream"`` / ``"image/png"``），
        供 renderer 生成 Content-Type header field。
    :var binary_file_field: 单一文件 :class:`FieldDecl`（如 ``body: UploadFile``），
        由 :func:`stoma.openapi.fields.build_upload_file_field_line` 派生（schema
        固定为 ``UploadFile``，仅 name 由 renderer 决定）；spec 未声明 binary 时为 ``None``。
    """

    media_type: str | None = None
    binary_file_field: FieldDecl | None = None


@dataclass
class ScalarRequestBodyFields:
    """primitive schema（任意 content type）→ 单字段 body。

    渲染为 ``body: Annotated[<type>, Body(media_type=<media_type>)]``，
    wire 是裸值（``Body()`` 默认 ``embed=False``）。

    Scalar body 没有隐含的 Content-Type（Playwright 无法从裸值推断），renderer 必须
    把 media_type 嵌入 ``Body(media_type=...)``，由 client 通过 ``param_info.media_type``
    派生 Content-Type header（不走 Header field 路径）。

    :var scalar_field: 单字段 :class:`FieldDecl`（如
        ``body: Annotated[int, Body(media_type="application/json")]``），
        由 :func:`stoma.openapi.fields.build_scalar_body_line` 派生；
        空 schema / 不支持 primitive 时为 ``None``。
    """

    scalar_field: FieldDecl | None = None


class Endpoint[ParameterT: BaseModel, RequestBodyT: BaseModel, ResponseT: BaseModel](
    BaseModel,
):
    """单个接口的完整信息（IR - Intermediate Representation）。

    :var operation_id: OpenAPI ``operationId``，作为生成文件名的依据。
    :vartype operation_id: str
    :var method: HTTP 方法（``GET``/``POST``/``PUT``/``PATCH``/``DELETE``/``HEAD``/``OPTIONS``/``TRACE``）。
    :vartype method: str
    :var path: OpenAPI 路径模板（包含 ``{param}`` 占位符）。
    :vartype path: str
    :var summary: OpenAPI ``summary``，可为 ``None``。
    :vartype summary: str | None
    :var description: OpenAPI ``description``，可为 ``None``。
    :vartype description: str | None
    :var parameters: 该操作的全部参数（query / path / header），
        引用已由 parser 阶段展开。
    :vartype parameters: list[ParameterT]
    :var request_body: 请求体对象，可为 ``None``。
    :vartype request_body: RequestBodyT | None
    :var responses: ``状态码 -> 响应对象`` 映射；未声明响应时为 ``None``。
    :vartype responses: dict[str, ResponseT] | None
    :var spec_version: 当前 Endpoint 对应的 OpenAPI spec 主版本（``3.0``
        或 ``3.1``），供 renderer 按版本派发 reference 检测。
    :vartype spec_version: SpecVersion
    :var expanded_raw_request_body: 经 jsonref 展开后的 ``requestBody`` dict
        （由 :func:`expand_path_refs` 抽离出来），
        供 renderer 在判别 body 形态后直接读取 schema 内容。无 requestBody
        或非 requestBody 引用展开场景时为 ``None``。
    :vartype expanded_raw_request_body: dict[str, Any] | None
    """

    operation_id: str
    method: str
    path: str
    summary: str | None
    description: str | None
    parameters: list[ParameterT]
    request_body: RequestBodyT | None
    responses: dict[str, ResponseT] | None
    spec_version: SpecVersion
    expanded_raw_request_body: dict[str, Any] | None = None
