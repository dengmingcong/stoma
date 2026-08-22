"""API 响应封装与构造。

集中 :class:`Response`、:class:`BaseResponseSpec` 与 :func:`build_response`：

- :class:`Response` — 框架对外的统一响应包装（dataclass，泛型 ``T``）。
- :class:`BaseResponseSpec` — 响应协议抽象基类（泛型 ``T``），
  定义按状态码与 media type 严格校验响应的契约。
  子类 :class:`JSONResponseSpec` 与 :class:`RawResponseSpec`
  分别实现 JSON 与原始（``bytes`` / ``str``）两种响应处理。
- :func:`build_response` — 从 Playwright ``APIResponse`` 构造 ``Response[T]``，
  按 content-type 派发解析：JSON 路径用 ``T`` 验证，其他保持 ``None``。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from playwright.sync_api import APIResponse
from pydantic import TypeAdapter

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


class BaseResponseSpec[T](ABC):
    """响应协议抽象基类。

    定义按 HTTP 状态码与 media type 严格校验响应的契约。
    子类通过实现 :meth:`validate_response` 提供具体的响应解析逻辑，
    通常先调用 :meth:`_assert_status` 与 :meth:`_assert_media_type`
    做协议级强校验（不匹配抛 ``AssertionError``），
    再做具体解析（解析失败抛 :class:`ParseError` 或 :class:`ValidationError`），
    最后返回 ``T`` 类型的已校验数据。

    使用 ``ABC`` + ``@abstractmethod``（而非 Pydantic ``BaseModel``），
    因为 spec 不需要序列化，且 ``status_code`` 支持 ``Callable[[int], bool]``
    谓词形式（用于 OpenAPI ``default`` / ``4XX`` / ``5XX`` 等范围通配符），
    谓词与运行时响应对象都不属于 Pydantic 友好类型。

    设计要点：

    - ``status_code`` 既可是 ``int``（精确匹配 HTTP 状态码），
      也可是 ``Callable[[int], bool]``（谓词匹配）。
    - ``media_type`` 是精确字符串匹配（如 ``application/json``），
      也可使用 ``*`` 通配所有 media type。
      传入 content-type header 时会自动 strip ``;charset=...`` 等参数。

    :var status_code: 期望的 HTTP 状态码（``int``）或状态码谓词（``Callable[[int], bool]``）。
    :vartype status_code: int | Callable[[int], bool]
    :var media_type: 期望的 media type（如 ``application/json``），
        ``*`` 表示通配所有 media type。
    :vartype media_type: str
    """

    def __init__(
        self,
        status_code: int | Callable[[int], bool],
        media_type: str,
    ) -> None:
        """初始化响应协议基类。

        :param status_code: 期望的 HTTP 状态码（``int``）或状态码谓词（``Callable[[int], bool]``）。
        :param media_type: 期望的 media type（如 ``application/json``），
            ``*`` 表示通配所有 media type。
        """
        self.status_code = status_code
        self.media_type = media_type

    def _assert_status(self, actual: int) -> None:
        """断言实际状态码与 spec 匹配。

        ``status_code`` 为 ``int`` 时按等值匹配；
        为 ``Callable[[int], bool]`` 时调用谓词判断。
        不匹配抛 ``AssertionError``。

        :param actual: 实际 HTTP 状态码。
        :raise AssertionError: 实际状态码与 spec 不匹配。
        """
        if callable(self.status_code):
            assert self.status_code(actual), f"HTTP 状态码不匹配: 期望满足谓词，实际为 {actual}"
        else:
            assert actual == self.status_code, f"HTTP 状态码不匹配: 期望 {self.status_code}，实际为 {actual}"

    def _assert_media_type(self, content_type: str) -> None:
        """断言实际 content-type 与 spec 的 media_type 匹配。

        自动 strip ``;charset=...`` 等参数，再做小写精确匹配。
        ``media_type`` 为 ``*`` 时通配所有 media type（始终匹配）。

        :param content_type: 实际 content-type header 值，可能带 ``;charset=...`` 后缀。
        :raise AssertionError: 实际 content-type 与 spec 不匹配。
        """
        if self.media_type == "*":
            return
        main = content_type.split(";", 1)[0].strip().lower()
        spec_media_type = self.media_type.strip().lower()
        assert main == spec_media_type, f"Content-Type 不匹配: 期望 {self.media_type}，实际为 {main or '(空)'}"

    @abstractmethod
    def validate_response(self, response: APIResponse) -> T:
        """校验并解析响应为 ``T`` 类型。

        子类必须实现：先调用 :meth:`_assert_status` 与 :meth:`_assert_media_type`
        做协议级强校验（不匹配抛 ``AssertionError``），
        再做具体解析（解析失败抛 :class:`ParseError` 或 :class:`ValidationError`），
        最后返回 ``T`` 类型的已校验数据。

        :param response: Playwright 响应对象。
        :return: 已校验的响应数据，类型为 ``T``。
        :raise AssertionError: status 或 content-type 与 spec 不匹配。
        :raise ParseError: 响应解析失败。
        :raise ValidationError: 响应数据验证失败。
        """
        raise NotImplementedError


class JSONResponseSpec[T](BaseResponseSpec[T]):
    """JSON 响应协议。

    在 :class:`BaseResponseSpec` 的协议级强校验基础上，
    用 :class:`pydantic.TypeAdapter` 按 ``model`` 校验 JSON body，
    并返回强类型的 ``T`` 实例。

    设计要点：

    - ``adapter``：构造时通过 :class:`pydantic.TypeAdapter` 编译 ``model``，
      :meth:`validate_response` 直接复用同一适配器实例，
      避免每次调用都重新构造。
    - 异常映射：JSON 解析失败抛 :class:`ParseError`（带原始 ``response_text``）；
      Pydantic 校验失败抛 stoma :class:`ValidationError`（带 Pydantic ``errors``）。

    :var status_code: 期望的 HTTP 状态码（``int``）或状态码谓词（``Callable[[int], bool]``）。
    :vartype status_code: int | Callable[[int], bool]
    :var media_type: 期望的 media type（如 ``application/json``），
        ``*`` 表示通配所有 media type。
    :vartype media_type: str
    :var adapter: Pydantic :class:`TypeAdapter` 实例，按 ``model`` 校验 body。
    :vartype adapter: TypeAdapter[T]
    """

    def __init__(
        self,
        status_code: int | Callable[[int], bool],
        media_type: str,
        model: type[T],
    ) -> None:
        """初始化 JSON 响应协议。

        :param status_code: 期望的 HTTP 状态码（``int``）或状态码谓词（``Callable[[int], bool]``）。
        :param media_type: 期望的 media type（如 ``application/json``），
            ``*`` 表示通配所有 media type。
        :param model: 用于校验响应 body 的 Pydantic 模型类。
        """
        super().__init__(status_code, media_type)
        self.adapter: TypeAdapter[T] = TypeAdapter(model)

    def validate_response(self, response: APIResponse) -> T:
        """校验并解析 JSON 响应为 ``T`` 类型实例。

        流程：

        1. 从 ``response.headers`` 取 content-type，并调用
           :meth:`_assert_status` 与 :meth:`_assert_media_type` 做协议级强校验。
        2. 调用 ``response.json()`` 解析 body；解析失败抛 :class:`ParseError`。
        3. 调用 ``self.adapter.validate_python(payload)`` 按 ``model`` 校验；
           校验失败抛 stoma :class:`ValidationError`（带 Pydantic ``errors``）。

        :param response: Playwright 响应对象。
        :return: 已校验的 Pydantic 模型实例，类型为 ``T``。
        :raise AssertionError: status 或 content-type 与 spec 不匹配。
        :raise ParseError: JSON 解析失败。
        :raise ValidationError: 响应数据验证失败。
        """
        content_type = response.headers.get("content-type", "") if response.headers else ""
        self._assert_status(response.status)
        self._assert_media_type(content_type)

        try:
            payload: Any = response.json()
        except Exception as e:
            fallback_text = ""
            try:
                fallback_text = response.text() if hasattr(response, "text") else ""
            except Exception:
                pass
            msg = f"响应 JSON 解析失败: {e}"
            raise ParseError(msg, response_text=fallback_text) from e

        try:
            validated = self.adapter.validate_python(payload)
        except Exception as e:
            msg = f"响应数据验证失败: {e}"
            errors: list[dict[str, Any]] = []
            # Pydantic 的 ValidationError 才有 .errors() 方法。
            if hasattr(e, "errors"):
                errors = list(e.errors())  # type: ignore[no-any-return]
            raise ValidationError(msg, errors=errors) from e

        return validated  # type: ignore[no-any-return]


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


__all__ = ["Response", "BaseResponseSpec", "JSONResponseSpec", "build_response"]
