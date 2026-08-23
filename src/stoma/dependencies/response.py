"""API 响应封装与协议类。

- :class:`Response` — 框架对外的统一响应包装（dataclass），
  通过 :meth:`Response.expect` 选择响应协议并解析为强类型结果。
- :class:`BaseResponseSpec` — 响应协议抽象基类（泛型 ``T``），
  定义按 HTTP 状态码与 media type 严格校验响应的契约。
- :class:`ResponseSpec` — 通用响应协议（泛型 ``T``），
  处理 JSON / 标量 / 二进制等已知类型的响应：通过 ``expected_type`` 决定派发路径——
  ``expected_type is bytes`` 时直接返回 ``response.body()`` 的原始字节；
  其他 ``expected_type``（如 Pydantic 模型、``int``、``str``、``dict`` 等）走
  :meth:`pydantic.TypeAdapter.validate_json` 路径。
- :class:`EmptyResponseSpec` — 空响应协议，仅校验 HTTP 状态码，
  适用于 204 No Content、无响应 schema 或无法确定类型的描述性响应。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, cast

from playwright.sync_api import APIResponse
from pydantic import TypeAdapter

from stoma.exceptions import ValidationError


@dataclass
class Response:
    """框架对外的统一响应包装。

    始终返回 :class:`Response`，不论 HTTP 状态码是否为错误。
    调用方通过 ``raw.status`` 判断请求成功/失败，
    并按需调用 :meth:`expect` 选定响应协议后获得强类型数据。

    设计要点：

    - ``raw``：Playwright 原始响应对象，类型为 ``playwright.sync_api.APIResponse``，
      提供完整 HTTP 协议层访问（``status`` / ``headers`` / ``text()`` / ``body()`` / ``json()``）。

    :var raw: Playwright 原始响应对象。
    :vartype raw: APIResponse

    Example::

        response = client.send(GetUsers(limit=10))
        users = response.expect(GetUsers.on_200)  # 类型为 list[UserData]
    """

    raw: APIResponse

    def expect[T](self, spec: BaseResponseSpec[T]) -> T:
        """按 ``spec`` 协议校验并解析响应。

        ``T`` 通过 PEP 695 泛型方法从 ``spec`` 的类型参数自动推断。
        本方法不做额外校验逻辑——直接复用 :meth:`BaseResponseSpec.validate_response`，
        让协议类保持单一职责。

        :param spec: 本次响应所采用的协议（``BaseResponseSpec`` 子类实例）。
        :return: 已校验并解析的响应数据，类型为 ``T``。
        :raise AssertionError: status 或 content-type 与 spec 不匹配。
        :raise ValidationError: 响应解析或校验失败。
        """
        return spec.validate_response(self.raw)


class BaseResponseSpec[T](ABC):
    """响应协议抽象基类。

    定义按 HTTP 状态码与 media type 严格校验响应的契约。
    子类通过实现 :meth:`validate_response` 提供具体的响应解析逻辑，
    通常先调用 :meth:`_assert_status` 与 :meth:`_assert_media_type`
    做协议级强校验（不匹配抛 ``AssertionError``），
    再做具体解析（解析失败抛 :class:`ValidationError`），
    最后返回 ``T`` 类型的已校验数据。

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

        :param response: Playwright 响应对象。
        :return: 已校验的响应数据，类型为 ``T``。
        :raise AssertionError: status 或 content-type 与 spec 不匹配。
        :raise ValidationError: 响应解析或校验失败。
        """
        raise NotImplementedError


class ResponseSpec[T](BaseResponseSpec[T]):
    """通用响应协议。

    在 :class:`BaseResponseSpec` 的协议级强校验基础上，
    按 ``expected_type`` 派发响应处理：

    - ``expected_type is bytes`` → 直接返回 ``response.body()`` 的原始字节，
      适用于图片、protobuf、二进制下载等。
    - 其他 ``expected_type``（如 Pydantic 模型、``int``、``str``、``dict`` 等）
      → :class:`pydantic.TypeAdapter.validate_json` 按 ``expected_type`` 校验
      JSON body 并返回强类型 ``T`` 实例。

    设计要点：

    - **统一 adapter 派发**：构造时通过 :class:`pydantic.TypeAdapter` 编译
      ``expected_type``，``validate_response`` 直接复用同一适配器实例，
      避免每次调用都重新构造。
    - **bytes 走特殊路径**：JSON 解码要求 UTF-8 文本，二进制数据无法被
      ``validate_json`` 解析，所以 ``bytes`` 必须先短路返回 ``response.body()``
      而非走 JSON 路径。
    - **统一异常类型**：JSON 解析失败与 Pydantic schema 不匹配都映射为
      :class:`ValidationError`，上层只需捕获一种异常类型。

    :var status_code: 期望的 HTTP 状态码（``int``）或状态码谓词（``Callable[[int], bool]``）。
    :vartype status_code: int | Callable[[int], bool]
    :var media_type: 期望的 media type（如 ``application/json``），
        ``*`` 表示通配所有 media type。
    :vartype media_type: str
    :var expected_type: 期望验证为的类型（如 Pydantic 模型类、``int``、``str``、``bytes``）。
    :vartype expected_type: type[T]
    :var adapter: Pydantic :class:`TypeAdapter` 实例，按 ``expected_type`` 校验 body。
    :vartype adapter: TypeAdapter[T]

    Example::

        # JSON 对象响应（如用户数据）。
        spec = ResponseSpec(200, "application/json", UserData)
        result = response.expect(spec)  # → UserData

        # JSON 标量响应（如计数）。
        spec = ResponseSpec(200, "application/json", int)
        result = response.expect(spec)  # → int

        # 字节响应（如图片下载）。
        spec = ResponseSpec(200, "image/png", bytes)
        result = response.expect(spec)  # → bytes
    """

    def __init__(
        self,
        status_code: int | Callable[[int], bool],
        media_type: str,
        expected_type: type[T],
    ) -> None:
        """初始化通用响应协议。

        :param status_code: 期望的 HTTP 状态码（``int``）或状态码谓词（``Callable[[int], bool]``）。
        :param media_type: 期望的 media type（如 ``application/json``），
            ``*`` 表示通配所有 media type。
        :param expected_type: 期望验证为的类型（如 Pydantic 模型类、``int``、``str``、``bytes``）。
        """
        super().__init__(status_code, media_type)
        self.expected_type: type[T] = expected_type
        self.adapter: TypeAdapter[T] = TypeAdapter(expected_type)

    def validate_response(self, response: APIResponse) -> T:
        """校验并解析响应为 ``T`` 类型实例。

        流程：

        1. 调用 :meth:`_assert_status` 与 :meth:`_assert_media_type` 做协议级强校验。
        2. ``expected_type is bytes`` → 直接返回 ``response.body()``；
           其他 ``expected_type`` → 调用 ``self.adapter.validate_json(response.body())``
           按 ``expected_type`` 校验，失败抛 :class:`ValidationError`（带 Pydantic ``errors``）。

        :param response: Playwright 响应对象。
        :return: 已校验的响应数据，类型为 ``T``。
        :raise AssertionError: status 或 content-type 与 spec 不匹配。
        :raise ValidationError: 响应解析或校验失败。
        """
        self._assert_status(response.status)
        self._assert_media_type(response.headers.get("content-type", ""))

        if self.expected_type is bytes:
            return cast(T, response.body())

        try:
            return self.adapter.validate_json(response.body())
        except Exception as e:
            msg = f"响应数据验证失败: {e}"
            errors: list[dict[str, Any]] = []
            # Pydantic 的 ValidationError 才有 .errors() 方法。
            if hasattr(e, "errors"):
                errors = list(e.errors())
            raise ValidationError(msg, errors=errors) from e


class EmptyResponseSpec(BaseResponseSpec[None]):
    """空响应协议。

    仅校验 HTTP 状态码，不解析响应体。适用于：

    - 204 No Content 等无 body 的响应。
    - OpenAPI 描述中仅有 ``description``、无 ``content`` / 无 ``schema`` 的 status code，
      框架无法为其派生强类型时的兜底。
    - 调用方只关心请求成功与否、不需要解析 body 的场景。

    设计要点：

    - **覆写 ``__init__``**：仅接收 ``status_code``，不接收 ``media_type``。
      内部以 ``media_type="*"`` 占位——空响应协议不关心媒体类型，
      屏蔽调用方对 ``media_type`` 的输入以减少误用。
    - **仅断言 status**：``validate_response`` 不做 media type 与 body 校验，
      任何 content-type 与 body 内容都被忽略。

    :var status_code: 期望的 HTTP 状态码（``int``）或状态码谓词（``Callable[[int], bool]``）。
    :vartype status_code: int | Callable[[int], bool]

    Example::

        spec = EmptyResponseSpec(204)
        response.expect(spec)  # 仅校验 status == 204，忽略 body。
    """

    def __init__(self, status_code: int | Callable[[int], bool]) -> None:
        """初始化空响应协议。

        :param status_code: 期望的 HTTP 状态码（``int``）或状态码谓词（``Callable[[int], bool]``）。
        """
        super().__init__(status_code, media_type="*")

    def validate_response(self, response: APIResponse) -> None:
        """仅校验 HTTP 状态码。

        不校验 media type，也不解析 body。任何 content-type 与 body 内容都被忽略。

        :param response: Playwright 响应对象。
        :raise AssertionError: 实际状态码与 spec 不匹配。
        """
        self._assert_status(response.status)


__all__ = ["Response", "BaseResponseSpec", "ResponseSpec", "EmptyResponseSpec"]
