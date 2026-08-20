"""API 响应封装与构造。

集中 :class:`Response` 与 :func:`build_response`：

- :class:`Response` — 框架对外的统一响应包装（dataclass，泛型 ``T``）。
- :func:`build_response` — 从 Playwright ``APIResponse`` 构造 ``Response[T]``，
  按 content-type 派发解析：JSON 路径用 ``T`` 验证，其他保持 ``None``。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from playwright.sync_api import APIResponse

from stoma.exceptions import ParseError, ValidationError
from stoma.openapi.media_type import is_json_media_type
from stoma.routing import APIRoute


@dataclass
class Response[T]:
    """框架对外的统一响应封装。

    始终返回 :class:`Response`，不论 HTTP 状态码是否为错误。
    调用方通过 ``raw.status`` 判断请求成功/失败。

    ``Response`` 是 dataclass（而非 Pydantic BaseModel），
    因为 ``raw`` 字段持有 Playwright 的 :class:`APIResponse` 对象，该对象不是 Pydantic
    可识别的类型。使用 dataclass 既避免了 ``arbitrary_types_allowed`` 的额外配置，
    又保留了简洁的类型注解能力。

    设计要点：

    - ``raw``：Playwright 原始响应对象，类型为 ``playwright.sync_api.APIResponse``，
      提供完整 HTTP 协议层访问（``status`` / ``headers`` / ``text()`` / ``body()`` / ``json()``）。
    - ``validated``：仅当响应 content-type 为 JSON 时填充，
      用 Pydantic 验证后的 ``T`` 类型实例；其他 content-type 时为 ``None``。

    字段说明：

    - ``raw``：Playwright 原始响应对象，提供完整 HTTP 协议层访问。
    - ``validated``：JSON 响应解析后的 Pydantic 模型实例，其他 content-type 时为 None。

    :var raw: Playwright 原始响应对象。
    :vartype raw: APIResponse
    :var validated: JSON 响应解析后的 Pydantic 模型实例，其他 content-type 时为 None。
    :vartype validated: T | None

    Example::

        response = client.send(endpoint)
        if response.raw.status == 200:
            user = response.validated  # 类型为 UserData
        else:
            log.error(f"failed: {response.raw.status}")
    """

    raw: APIResponse
    validated: T | None = None


def build_response[T](api_route: APIRoute[T], api_response: APIResponse) -> Response[T]:
    """从 Playwright :class:`APIResponse` 构造 :class:`Response[T]`。

    流程：
    1. 直接持有 Playwright 原始响应对象作为 raw
    2. 解析 content-type 派发：JSON 路径用 T 验证，其他保持 None
    3. 4xx/5xx 不抛错，由 raw.status 判断

    :param api_route: APIRoute 实例（提供 T）。
    :param api_response: Playwright 响应对象。
    :return: 包装后的 :class:`Response[T]`。
    :raise ParseError: JSON 解析失败。
    :raise ValidationError: JSON 验证失败。
    """
    dependant = api_route._get_dependant()

    # 1. 解析 content-type
    content_type = api_response.headers.get("content-type", "") if api_response.headers else ""
    media_type = content_type.split(";")[0].strip().lower()

    # 2. 特殊：204 No Content → validated = None
    if api_response.status == 204:
        return Response[T](raw=api_response, validated=None)

    # 2b. 空 body（204 / HEAD / 304 / 其他空响应）→ 跳过 JSON 解析
    # 调用方按 raw.status + raw.text() 自行判断响应是空还是具体 model
    try:
        if not api_response.body():
            return Response[T](raw=api_response, validated=None)
    except Exception:
        pass

    # 3. 无 json_response_schema 时直接退出，不进入 is_json_media_type 分支
    # 否则会触发裸字符串响应体（application/json + 非 JSON body）的 ParseError。
    # 仅当 schema 存在时才有必要解析 JSON 并填充 validated。
    if dependant.json_response_schema is None:
        return Response[T](raw=api_response, validated=None)

    # 4. 仅当 content-type 为 JSON 时才解析并填充 validated
    if is_json_media_type(media_type):
        try:
            payload: Any = api_response.json()
        except Exception as e:
            fallback_text = ""
            try:
                fallback_text = api_response.text() if hasattr(api_response, "text") else ""
            except Exception:
                pass
            msg = f"响应 JSON 解析失败: {e}"
            raise ParseError(msg, response_text=fallback_text) from e

        assert dependant.json_response_schema_adapter is not None
        try:
            validated = dependant.json_response_schema_adapter.validate_python(payload)  # type: ignore[no-any-return]
        except Exception as e:
            msg = f"响应数据验证失败: {e}"
            errors: list[dict[str, Any]] = []
            # Pydantic 的 ValidationError 才有 .errors() 方法
            if hasattr(e, "errors"):
                errors = list(e.errors())  # type: ignore[no-any-return]
            raise ValidationError(msg, errors=errors) from e

        return Response[T](raw=api_response, validated=validated)

    # 5. 非 JSON 响应 + 有 schema：无法校验，validated = None
    return Response[T](raw=api_response, validated=None)


__all__ = ["Response", "build_response"]
