"""OpenAPI 规范的预处理函数。

stoma 的「全局 ``models.py`` + 每个 endpoint 一个 ``route.py``」结构
依赖两份前置规整，否则 ``datamodel-code-generator`` 生成的 ``models.py``
与 ``route.py`` 之间的命名对不上、``Body(embed=True)`` 语义也对不上：

- ``inject_inline_titles``：给内联 object 注入 ``title`` 字段，使
  ``datamodel-code-generator`` 用 ``<OperationId>Request`` /
  ``<OperationId>Response`` 派生类名。
- ``unwrap_embed_wrappers``：把 ``{data: User}`` 这样的单属性 wrapper
  解包成 ``User``，并把 wrapper 字段名记到 :class:`EmbedInfo` 里
  供 ``route.py`` 渲染 ``Body(embed=True)`` 使用。
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from typing import Any

from src.openapi.models import Endpoint

# 在下划线、连字符，或 camelCase 边界处切分单词。
_WORD_SPLIT_PATTERN = re.compile(r"[_-]+|(?<=[a-z0-9])(?=[A-Z])")


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
    :var model_name: wrapper 解包后内层 schema 对应的模型名（已经过
        ``inject_inline_titles`` 注入；如果是 ``$ref``，则等于 ref
        末段的 schema 名）。
    :vartype model_name: str
    """

    operation_id: str
    field_name: str
    model_name: str


def operation_id_to_pascal(operation_id: str) -> str:
    """把 operationId 转为 PascalCase 类名。

    支持 snake_case（``list_users``）、camelCase（``listUsers``）、
    PascalCase（``ListUsers``）和含连字符（``list-users``）四种格式。

    :param operation_id: 原始 operationId。
    :return: PascalCase 类名。
    """
    normalized = operation_id.replace("-", "_")
    words = _WORD_SPLIT_PATTERN.split(normalized)
    return "".join(word.capitalize() for word in words if word)


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


def _find_response_schema(
    spec: dict[str, Any],
    endpoint: Endpoint,
) -> dict[str, Any] | None:
    """在 spec 字典中定位 endpoint 200/201 响应的 schema dict，找不到返回 None。"""
    op = spec.get("paths", {}).get(endpoint.path, {}).get(endpoint.method)
    if not isinstance(op, dict):
        return None
    responses = op.get("responses", {})
    if not isinstance(responses, dict):
        return None
    for status in ("200", "201"):
        resp = responses.get(status)
        if not isinstance(resp, dict):
            continue
        content = resp.get("content", {})
        json = content.get("application/json", {})
        if not isinstance(json, dict):
            continue
        schema = json.get("schema")
        if isinstance(schema, dict):
            return schema
    return None


def _is_inline_object(schema: dict[str, Any]) -> bool:
    """检测是否是「需要注入 title」的内联 object。

    已带 ``title`` 的 schema（来自 ``$ref`` 解析后的命名 schema）跳过，
    避免覆盖正确的类名。
    """
    if "$ref" in schema:
        return False
    if schema.get("title"):
        return False
    if schema.get("type") != "object":
        return False
    properties = schema.get("properties")
    return isinstance(properties, dict) and len(properties) > 0


def inject_inline_titles(
    spec: dict[str, Any],
    endpoints: list[Endpoint],
) -> dict[str, Any]:
    """为每个 endpoint 的内联 object 注入 title。

    行为：

    - 内联 object（无 ``$ref``、有 ``properties``）→ 注入
      ``title = {PascalCase(operation_id)}Request``（请求体）或
      ``{PascalCase(operation_id)}Response``（响应）。
    - ``$ref`` schema → 不动（``$ref`` 由 datamodel-code-generator 自行解析）。
    - 纯 scalar 或没有任何 property 的 object → 不动。

    :param spec: 解析后的 OpenAPI 规范字典（已被 prance 展开 ``$ref``）。
    :param endpoints: 通过 :meth:`OpenAPIParser.get_endpoints` 获取的 IR 列表。
    :return: 新的 spec 字典，不修改入参。
    """
    new_spec = copy.deepcopy(spec)
    for endpoint in endpoints:
        if not endpoint.operation_id:
            continue
        pascal = operation_id_to_pascal(endpoint.operation_id)

        body_schema = _find_request_body_schema(new_spec, endpoint)
        if isinstance(body_schema, dict) and _is_inline_object(body_schema):
            body_schema["title"] = f"{pascal}Request"

        resp_schema = _find_response_schema(new_spec, endpoint)
        if isinstance(resp_schema, dict) and _is_inline_object(resp_schema):
            resp_schema["title"] = f"{pascal}Response"

    return new_spec


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


def _update_embed_model_names(
    spec: dict[str, Any],
    endpoints: list[Endpoint],
    embed_infos: list[EmbedInfo],
) -> list[EmbedInfo]:
    """根据最终 spec 更新 embed 信息里的 model_name。

    ``unwrap_embed_wrappers`` 在 title 注入之前记录 ``EmbedInfo``，
    此时内层 schema 还没有 title 所以 ``model_name`` 可能是 ``"Unknown"``。
    本函数在 ``inject_inline_titles`` 之后重新读取每个 endpoint 的
    请求体 schema 顶层，提取最新 ``title`` 或 ``$ref`` 末段。

    :param spec: 经 ``unwrap_embed_wrappers`` + ``inject_inline_titles`` 之后的 spec。
    :param endpoints: 通过 :meth:`OpenAPIParser.get_endpoints` 获取的 IR 列表。
    :param embed_infos: ``unwrap_embed_wrappers`` 输出的 embed 信息列表。
    :return: ``model_name`` 已更新到最新 spec 的 embed 信息列表。
    """
    endpoint_by_id = {e.operation_id: e for e in endpoints if e.operation_id}
    updated: list[EmbedInfo] = []
    for info in embed_infos:
        endpoint = endpoint_by_id.get(info.operation_id)
        if endpoint is None:
            updated.append(info)
            continue
        body_schema = _find_request_body_schema(spec, endpoint)
        if isinstance(body_schema, dict):
            new_name = _resolve_model_name(body_schema)
        else:
            new_name = info.model_name
        updated.append(
            EmbedInfo(
                operation_id=info.operation_id,
                field_name=info.field_name,
                model_name=new_name,
            )
        )
    return updated


def transform_spec_for_generation(
    spec: dict[str, Any],
    endpoints: list[Endpoint],
) -> tuple[dict[str, Any], list[EmbedInfo]]:
    """按顺序运行所有转换，返回新 spec 与 embed 信息。

    调用顺序：先解包 embed wrapper（让原本被包起来的内层 schema 暴露
    在顶层），再注入 title（这样 wrapper 解包出的内层 inline object
    也能拿到 title），最后根据新 spec 重新读取 embed 信息的
    ``model_name``。

    :param spec: 解析后的 OpenAPI 规范字典。
    :param endpoints: 通过 :meth:`OpenAPIParser.get_endpoints` 获取的 IR 列表。
    :return: ``(new_spec, embed_infos)``。
    """
    new_spec, embed_infos = unwrap_embed_wrappers(spec, endpoints)
    new_spec = inject_inline_titles(new_spec, endpoints)
    new_embed_infos = _update_embed_model_names(new_spec, endpoints, embed_infos)
    return new_spec, new_embed_infos
