"""API 请求参数构造。

数据类：
- :class:`BodyItem` — raw body 单字段 ``(alias, dumped)`` 元组。
- :class:`RawPayload` — raw body 复合值 + 可选 ``media_type``。
- :class:`RequestBodyKind` — 请求体类型枚举（NONE / MULTIPART_FORM /
  URLENCODED_FORM / RAW / BINARY）。
- :class:`RequestBody` — 序列化的请求体元信息。
- :class:`Request` — 完整请求参数（method / path / params / headers / body）。

构造函数：
- :func:`build_request` — 从 ``APIRoute`` 构造 ``Request``。
- 私有 helper：``_interpolate_path_params`` / ``_collect_query_params`` /
  ``_serialize_header_params`` / ``_serialize_body_params`` /
  ``_build_raw_body`` / ``_fill_form_field``。

``RequestBodyKind`` 与 ``RequestBody`` 是 Playwright 发送层的中间表示，
与 OpenAPI spec 的 ``requestBody`` 概念（openapi-pydantic 的同名 model）无
对应关系，使用时注意区分。
"""

from __future__ import annotations

import mimetypes
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum, auto
from typing import Any, NamedTuple

from playwright.sync_api import FilePayload, FormData
from pydantic import BaseModel

from stoma.dependencies import Dependant, ModelField
from stoma.dependencies.annotation import field_annotation_is_complex
from stoma.params import Body, UploadFile
from stoma.routing import APIRoute


class BodyItem(NamedTuple):
    """body 项。"""

    alias: str
    dumped: dict[str, Any] | Any


class RawPayload(NamedTuple):
    """对应 Postman raw body。"""

    value: Any
    media_type: str | None = None


class RequestBodyKind(Enum):
    """请求体类型枚举。

    :var NONE: 相当于 Postman 'none' body，表示无请求体。
    :var MULTIPART_FORM: 相当于 Postman 'form-data' body，使用 multipart/form-data 编码。
    :var URLENCODED_FORM: 相当于 Postman 'x-www-form-urlencoded' body，使用 application/x-www-form-urlencoded 编码。
    :var RAW: 相当于 Postman 'raw' body，使用 application/json 或其他纯文本类型编码。
    :var BINARY: 相当于 Postman 'binary' body，发送单个文件，Content-Type 由文件 mimeType 决定。
    """

    NONE = auto()
    MULTIPART_FORM = auto()
    URLENCODED_FORM = auto()
    RAW = auto()
    BINARY = auto()


@dataclass
class RequestBody:
    """请求体数据结构。

    用于在序列化过程中携带不同类型请求体的元信息。

    :var kind: 请求体类型。
    :var raw_data: 原始请求体数据（当 kind 为 RAW 时），以 :class:`RawPayload`
        承载 ``value`` 与可选 ``media_type``。

        参考 Postman Body 的 raw 模式。

    :var form_data: 表单请求体数据（当 kind 为 URLENCODED 或 MULTIPART 时）。
    :var binary_file: 二进制请求体数据（当 kind 为 BINARY 时），以 Playwright
        :data:`FilePayload` 结构 ``{name, mimeType, buffer}`` 承载。

        参考 Postman Body 的 binary 模式。
    """

    kind: RequestBodyKind
    raw_data: RawPayload | None = None
    form_data: FormData | None = None
    binary_file: FilePayload | None = None


class Request(NamedTuple):
    """请求参数元组。

    从 :func:`build_request` 返回，提供命名字段以提升可读性。

    :var method: HTTP 方法。
    :var path: 相对路径。
    :var params: 查询参数字典。
    :var headers: 请求头字典。
    :var body: 请求体数据结构。
    """

    method: str
    path: str
    params: dict[str, Any]
    headers: dict[str, str]
    body: RequestBody


def _fill_form_data(form_data: FormData, model_field: ModelField, value: Any) -> None:
    """填充函数级 Form 字段到 FormData。

    根据 ``value`` 类型派发（Pydantic 已保证类型一致性）：

    - ``list``：逐个元素 ``form_data.append(alias, elem)``，
      同名多 part。
    - 其他标量：``form_data.set(alias, value)``，原值传递，不做 JSON 序列化。

    ``None`` 值（字段本身或 list 元素）一律跳过；空 list 相当于整个字段不出现。
    字段类型由 ``src.routing`` 阶段的 ``validate_form_field_annotation`` 校验，
    本函数不再对运行时值做类型检查（信任 Pydantic）。

    :param form_data: 待填充的表单。
    :param model_field: Form 字段定义。
    :param value: 字段值。
    """
    if value is None:
        return
    if isinstance(value, list):
        for element in value:
            if element is None:
                continue
            form_data.append(model_field.alias, element)
        return
    form_data.set(model_field.alias, value)


def build_request(api_route: APIRoute) -> Request:
    """从 ``api_route`` 提取请求参数。

    返回 :class:`Request` 命名元组，包含 method、path、params、headers、body。

    :param api_route: APIRoute 实例。
    :return: 完整请求参数。
    """
    dependant = api_route._get_dependant()
    path = _interpolate_path_params(api_route, dependant)
    params = _collect_query_params(api_route, dependant)
    headers = _serialize_header_params(api_route, dependant)
    body = _serialize_body_params(api_route, dependant)
    return Request(
        method=dependant.method,
        path=path,
        params=params,
        headers=headers,
        body=body,
    )


def _interpolate_path_params(api_route: APIRoute, dependant: Dependant) -> str:
    """插值路径参数（将 {param} 占位符替换为实际值）。

    :return: 插值后的相对路径字符串。
    """
    path = dependant.path
    for model_field in dependant.path_params:
        value = getattr(api_route, model_field.name)
        placeholder = f"{{{model_field.alias}}}"
        path = path.replace(placeholder, str(value))
    return path


def _collect_query_params(api_route: APIRoute, dependant: Dependant) -> dict[str, Any]:
    """收集查询参数为 dict（Playwright 自动拼接为 query string）。

    规则：
    - None 值：跳过
    - 其他类型：直接传递，Playwright 自动转换
    """
    query: dict[str, Any] = {}
    for model_field in dependant.query_params:
        value = getattr(api_route, model_field.name)
        if value is None:
            continue
        query[model_field.alias] = value
    return query


def _serialize_header_params(api_route: APIRoute, dependant: Dependant) -> dict[str, str]:
    """序列化请求头参数为 dict。

    规则：
    - None 值：跳过
    - 布尔值：转换为 'true'/'false'（HTTP 约定）
    - 其他类型：str() 转换（HTTP header 值必须是字符串）
    - 别名：使用 Annotated[Type, Header(alias="...")] 显式设置；否则 snake_case → kebab-case
    """
    headers: dict[str, str] = {}
    for model_field in dependant.header_params:
        value = getattr(api_route, model_field.name)
        if value is None:
            continue
        if isinstance(value, bool):
            value = "true" if value else "false"
        else:
            value = str(value)

        headers[model_field.alias] = value
    return headers


def _serialize_body_params(api_route: APIRoute, dependant: Dependant) -> RequestBody:
    """按请求体字段列表分派，序列化为 :class:`RequestBody`。

    Form 仅接受标量或 ``list[标量]`` 注解（含 Optional 形式）。
    ``form_body_params`` 字段由 :func:`_fill_form_field` 填充：list 值通过
    ``form_data.append`` 派发同名多 part。

    函数级 ``UploadFile`` 或 ``list[UploadFile]`` 由 routing 路由到
    ``file_body_params``，与 multipart 容器共用 ``FormData``。

    分派规则：

    - 存在文件字段（``file_body_params``）：multipart/form-data。
    - 仅有表单字段（``form_body_params``）：application/x-www-form-urlencoded。
    - 其余情况：application/json，沿用 FastAPI Body Multiple Parameters 规则。

    :param api_route: APIRoute 实例。
    :param dependant: 参数依赖定义。
    :return: 序列化后的请求体。
    """
    # raw-body 短路：``upload_as_multipart=False`` 时，整条 body 走 binary 字节。
    if not dependant.upload_as_multipart and dependant.file_body_params:
        field = dependant.file_body_params[0]
        value = getattr(api_route, field.name)
        if value is None:
            return RequestBody(kind=RequestBodyKind.BINARY, binary_file=None)
        if isinstance(value, UploadFile):
            data = value.path.read_bytes()
            mime, _ = mimetypes.guess_type(str(value.path))
            binary_file: FilePayload = {
                "name": str(value.path.name),
                "mimeType": mime if mime else "application/octet-stream",
                "buffer": data,
            }
            return RequestBody(
                kind=RequestBodyKind.BINARY,
                binary_file=binary_file,
            )
        # 启动期校验已保证 ``file_body_params`` 只有 ``UploadFile`` / ``list[UploadFile]``，
        # 这里仅是兜底，正常情况下不可达。
        msg = f"raw body 模式下字段 {field.name!r} 的值类型 {type(value).__name__} 不被支持"
        raise ValueError(msg)

    has_files = bool(dependant.file_body_params)
    form_data = FormData()

    for model_field in dependant.form_body_params:
        value = getattr(api_route, model_field.name)
        if value is None:
            continue
        _fill_form_data(form_data, model_field, value)

    for model_field in dependant.file_body_params:
        value = getattr(api_route, model_field.name)
        if value is None:
            continue
        # 注意：annotation 可能是 ``UploadFile | None`` / ``list[UploadFile] | None``，
        # ``field_info.annotation is UploadFile`` / ``get_origin(...) is list`` 会失效。
        # 这里改为按运行时值类型分发，对必填 / 可选（空列表视为跳过）都成立。
        if isinstance(value, UploadFile):
            form_data.set(model_field.alias, value.path)
        elif isinstance(value, list):
            # FormData.append 支持同一 key 多次出现，多次 part 对应多次同名字段。
            for upload_file in value:
                form_data.append(model_field.alias, upload_file.path)

    if has_files:
        return RequestBody(kind=RequestBodyKind.MULTIPART_FORM, form_data=form_data)
    # FormData 没有 ``__bool__`` / ``__len__``，空实例仍为真，必须用 ``_fields`` 判断非空。
    if form_data._fields:
        return RequestBody(kind=RequestBodyKind.URLENCODED_FORM, form_data=form_data)
    raw_body = _build_raw_body(api_route, dependant)
    media_type = None
    if raw_body is not None and len(dependant.pure_body_params) == 1:
        field = dependant.pure_body_params[0]
        param_info = field.param_info
        if (
            isinstance(param_info, Body)
            and not param_info.embed
            and not field_annotation_is_complex(field.field_info.annotation)
            and param_info.media_type is not None
        ):
            media_type = param_info.media_type
    return RequestBody(
        kind=RequestBodyKind.RAW,
        raw_data=RawPayload(value=raw_body, media_type=media_type),
    )


def _build_raw_body(api_route: APIRoute, dependant: Dependant) -> dict[str, Any]:
    """构建类似于 Postman Body 为 `raw` 的请求体。

    规则（参考 https://fastapi.tiangolo.com/tutorial/body-multiple-params/）：

    - 单 body 参数 + ``Body(embed=True)``：按 alias 嵌入。
    - 单 body 参数 + ``Body(embed=False)``：直接返回 dumped（BaseModel 平展、scalar 裸值）。
    - 多 body 参数：每字段独立按 alias 嵌入（``embed`` 被忽略）。

    :param api_route: APIRoute 实例。
    :param dependant: 参数依赖定义。
    :return: raw 请求体，无请求体字段时返回空字典。
    """
    if not dependant.pure_body_params:
        return {}

    has_multiple = len(dependant.pure_body_params) > 1
    body_items: list[BodyItem] = []

    # 循环中只做序列化，不做判断
    for model_field in dependant.pure_body_params:
        value = getattr(api_route, model_field.name)
        if value is None:
            continue

        # 序列化
        if isinstance(value, BaseModel):
            dumped = value.model_dump(by_alias=True, exclude_none=True)
        elif is_dataclass(value) and not isinstance(value, type):
            dumped = asdict(value)
        else:
            dumped = value

        body_items.append(BodyItem(model_field.alias, dumped))

    # 统一处理
    if not body_items:
        return {}

    # 多个 body 参数：必须嵌入，embed 被忽略
    if has_multiple:
        return {item.alias: item.dumped for item in body_items}

    # 单个 body 参数：仅 ``Body(embed=True)`` 时按 alias 嵌入；否则直接返回 dumped
    model_field = dependant.pure_body_params[0]
    param_info = model_field.param_info
    explicit_embed = isinstance(param_info, Body) and param_info.embed

    if explicit_embed:
        return {body_items[0].alias: body_items[0].dumped}

    return body_items[0].dumped


__all__ = [
    "BodyItem",
    "RawPayload",
    "Request",
    "RequestBody",
    "RequestBodyKind",
    "build_request",
]
