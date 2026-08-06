"""OpenAPI 规范的预处理函数。

stoma 的「全局 ``models.py`` + 每个 endpoint 一个 ``route.py``」结构
依赖前置规整（见 :mod:`src.openapi.parser` 里的 ``_fill_schema_titles``）。
本模块只负责一件事——解包 embed wrapper：

- ``unwrap_embed_wrappers``：把 ``{data: User}`` 这样的单属性 wrapper 解包
  成 ``User``，并把 wrapper 字段名记到 :class:`EmbedInfo` 里供 ``route.py``
  渲染 ``Body(embed=True)`` 使用。
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

from src.openapi.models import Endpoint


@dataclass(frozen=True)
class EmbedInfo:
    """Embed wrapper 信息。

    当 endpoint 的请求体是 ``{data: User}`` 这样的单属性 wrapper 时，
    ``route.py`` 渲染层需要这一份信息来决定加 ``Body(embed=True)``
    并使用 wrapper 的字段名作为接口类字段名。

    :var operation_id: 接口的 operationId。
    :vartype operation_id: str
    :var field_name: wrapper 字段名（即 ``route.py`` 里的接口类字段名）。
    :vartype field_name: str
    :var model_name: wrapper 解包后内层 schema 对应的模型名（已由
        ``_fill_schema_titles`` 注入的 title 决定；如果是 ``$ref``，则等于
        ref 末段的 schema 名）。
    :vartype model_name: str
    """

    operation_id: str
    field_name: str
    model_name: str


def _find_request_body_schema(
    spec: dict[str, Any],
    endpoint: Endpoint,
) -> dict[str, Any] | None:
    """在 spec 字典中定位 endpoint 请求体的 schema dict，找不到返回 None。"""
    op = spec.get("paths", {}).get(endpoint.path, {}).get(endpoint.method)
    if not isinstance(op, dict):
        return None
    rb = op.get("requestBody")
    if not isinstance(rb, dict):
        return None
    content = rb.get("content", {})
    json = content.get("application/json", {})
    if not isinstance(json, dict):
        return None
    schema = json.get("schema")
    return schema if isinstance(schema, dict) else None


def _detect_embed_wrapper(
    schema: dict[str, Any],
) -> tuple[str, dict[str, Any]] | None:
    """检测是否是 embed wrapper。

    embed wrapper 的特征：

    - ``type: object``
    - 有且仅有一个 property
    - 这个 property 在 ``required`` 列表中

    :param schema: 内联 object schema dict。
    :return: ``(field_name, inner_schema)`` 元组；不是 wrapper 返回 None。
    """
    if schema.get("type") != "object":
        return None
    properties = schema.get("properties")
    if not isinstance(properties, dict) or len(properties) != 1:
        return None
    required = schema.get("required") or []
    if not isinstance(required, list):
        return None
    field_name, inner = next(iter(properties.items()))
    if field_name not in required:
        return None
    if not isinstance(inner, dict):
        return None
    return field_name, inner


def _resolve_model_name(schema: dict[str, Any]) -> str:
    """从 schema 字典提取模型名（用于 :attr:`EmbedInfo.model_name`）。"""
    if "$ref" in schema:
        ref = schema["$ref"]
        # ``#/components/schemas/User`` → ``User``
        return ref.rsplit("/", 1)[-1]
    title = schema.get("title")
    if isinstance(title, str) and title:
        return title
    return "Unknown"


def unwrap_embed_wrappers(
    spec: dict[str, Any],
    endpoints: list[Endpoint],
) -> tuple[dict[str, Any], list[EmbedInfo]]:
    """解包 embed wrapper。

    把 ``{data: User}`` 形式的单属性 wrapper 替换为内层 schema ``User``，
    同时记录 :class:`EmbedInfo` 给 ``route.py`` 渲染层使用。嵌套
    embed（多层单属性 wrapper）递归解包直到非 wrapper。

    :param spec: 解析后的 OpenAPI 规范字典。
    :param endpoints: 通过 :meth:`OpenAPIParser.get_endpoints` 获取的 IR 列表。
    :return: ``(new_spec, embed_infos)``。
    """
    new_spec = copy.deepcopy(spec)
    embed_infos: list[EmbedInfo] = []
    for endpoint in endpoints:
        if not endpoint.operation_id:
            continue
        target = _find_request_body_schema(new_spec, endpoint)
        if not isinstance(target, dict):
            continue
        # 递归解包（嵌套多层的 wrapper 全部解开；只解包最外层 wrapper 的字段名）
        field_chain: list[str] = []
        current = target
        while True:
            detected = _detect_embed_wrapper(current)
            if detected is None:
                break
            field_name, inner = detected
            field_chain.append(field_name)
            current = inner
        if not field_chain:
            continue
        # 用最内层 schema 替换原 wrapper
        target.clear()
        target.update(current)
        embed_infos.append(
            EmbedInfo(
                operation_id=endpoint.operation_id,
                field_name=field_chain[0],
                model_name=_resolve_model_name(current),
            )
        )
    return new_spec, embed_infos


def transform_spec_for_generation(
    spec: dict[str, Any],
    endpoints: list[Endpoint],
) -> tuple[dict[str, Any], list[EmbedInfo]]:
    """运行所有转换，返回新 spec 与 embed 信息。

    :func:`_fill_schema_titles`（在 :mod:`src.openapi.parser` 里）已在
    prance 之前把所有需要的 title 注入到 spec 里（components 与 path
    inline 都覆盖，包括 embed wrapper 的内层）。所以本函数只需要
    做 wrapper 解包。

    :param spec: 解析后的 OpenAPI 规范字典。
    :param endpoints: 通过 :meth:`OpenAPIParser.get_endpoints` 获取的 IR 列表。
    :return: ``(new_spec, embed_infos)``。
    """
    return unwrap_embed_wrappers(spec, endpoints)
