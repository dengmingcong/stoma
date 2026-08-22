"""API 响应封装与协议类。

- :class:`Response` — 框架对外的统一响应包装（dataclass），
  通过 :meth:`Response.expect` 选择响应协议并解析为强类型结果。
- :class:`BaseResponseSpec` — 响应协议抽象基类（泛型 ``T``），
  定义按 HTTP 状态码与 media type 严格校验响应的契约；
  :class:`JSONResponseSpec` / :class:`RawResponseSpec`
  为其具体实现，分别处理 JSON 与原始（``bytes`` / ``str``）两种响应，
  通过 :meth:`validate_response` 返回强类型的 ``T`` 实例。

调用模式从「 ``Client.send`` 校验 + 填充 ``response.validated`` 」
改为「 ``Client.send`` 只发请求 → ``response.expect(spec)`` 触发校验」，
用户主动选择协议，``Response`` 不再持有已校验数据。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from playwright.sync_api import APIResponse
from pydantic import TypeAdapter

from stoma.exceptions import ParseError, ValidationError


@dataclass
class Response:
    """框架对外的统一响应包装。

    始终返回 :class:`Response`，不论 HTTP 状态码是否为错误。
    调用方通过 ``raw.status`` 判断请求成功/失败，
    并按需调用 :meth:`expect` 选定响应协议后获得强类型数据。

    ``Response`` 是 dataclass（而非 Pydantic BaseModel），
    因为 ``raw`` 字段持有 Playwright 的 :class:`APIResponse` 对象，该对象不是 Pydantic
    可识别的类型。使用 dataclass 既避免了 ``arbitrary_types_allowed`` 的额外配置，
    又保留了简洁的类型注解能力。

    设计要点：

    - ``raw``：Playwright 原始响应对象，类型为 ``playwright.sync_api.APIResponse``，
      提供完整 HTTP 协议层访问（``status`` / ``headers`` / ``text()`` / ``body()`` / ``json()``）。
    - 不持有已校验数据：``Response`` 不再内置 ``validated`` 字段。
      调用方通过 :meth:`expect` 显式指定协议来触发校验与解析。
      这样同一份 ``Response`` 可被不同协议反复校验（如先按 ``on_200`` 解析为
      ``UserData``，再按 ``on_5xx`` 解析为 ``ErrorBody``）。

    :var raw: Playwright 原始响应对象。
    :vartype raw: APIResponse

    Example::

        response = client.send(GetUsers(limit=10))
        if response.raw.status == 200:
            users = response.expect(GetUsers.on_200)  # 类型为 list[UserData]
        else:
            log.error(f"failed: {response.raw.status}")
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
        :raise ParseError: 响应解析失败（JSON 解码失败、文本解码失败等）。
        :raise ValidationError: 响应数据验证失败。
        """
        return spec.validate_response(self.raw)


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

        1. 调用 :meth:`_assert_status` 与 :meth:`_assert_media_type` 做协议级强校验。
        2. 调用 ``response.json()`` 解析 body；解析失败抛 :class:`ParseError`，
           并把 ``response.text()`` 作为 ``response_text`` 透传给调用方排错。
        3. 调用 ``self.adapter.validate_python(payload)`` 按 ``model`` 校验；
           校验失败抛 stoma :class:`ValidationError`（带 Pydantic ``errors``）。

        :param response: Playwright 响应对象。
        :return: 已校验的 Pydantic 模型实例，类型为 ``T``。
        :raise AssertionError: status 或 content-type 与 spec 不匹配。
        :raise ParseError: JSON 解析失败。
        :raise ValidationError: 响应数据验证失败。
        """
        self._assert_status(response.status)
        self._assert_media_type(response.headers.get("content-type", ""))

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
                errors = list(e.errors())
            raise ValidationError(msg, errors=errors) from e

        return validated


class RawResponseSpec[T](BaseResponseSpec[T]):
    """原始（``bytes`` / ``str``）响应协议。

    在 :class:`BaseResponseSpec` 的协议级强校验基础上，
    用 :class:`pydantic.TypeAdapter` 按 ``target_type`` 派发原始响应处理：

    - ``target_type = bytes`` → ``TypeAdapter(bytes)`` 返回 ``response.body()`` 的字节内容。
    - ``target_type = str`` → ``TypeAdapter(str)`` 把 ``response.body()`` 解码为 ``str``；
      解码失败（``UnicodeDecodeError``）被包装为 :class:`ParseError`。

    设计要点：

    - **类型参数显式传值**：``target_type`` 是构造时必填的位置参数。
      调用 ``RawResponseSpec(status_code, media_type)``（漏掉 ``target_type``）
      会由 Python 抛出 ``TypeError`` 提示缺参；同时如果 ``target_type`` 传入非
      ``bytes`` / ``str``，构造期就抛 ``TypeError`` 给出「必须 subscript
      ``RawResponseSpec[T]`` with bytes or str」提示——把错误挡在边界。
    - **统一 adapter 派发**：用 Pydantic :class:`TypeAdapter` 统一处理 bytes / str 两种路径，
      ``validate_response`` 中无需 ``if target is bytes / str`` 分支，
      直接 ``self.adapter.validate_python(response.body())`` 由 Pydantic 完成类型适配。
    - **强校验**：先走 :meth:`_assert_status` 与 :meth:`_assert_media_type`
      协议级检查；不通过抛 ``AssertionError``。
    - **裸字节路径** (``T=bytes``) ：``response.body()`` 不做解码，
      直接返回 bytes，适用于图片、protobuf、二进制下载等。
    - **文本路径** (``T=str``) ：``TypeAdapter(str).validate_python(bytes_data)``
      按 Pydantic lax 模式做 UTF-8 解码；非 UTF-8 内容抛 ``UnicodeDecodeError``，
      被包装为 :class:`ParseError` 而非透传，统一上层异常类型。

    :var status_code: 期望的 HTTP 状态码（``int``）或状态码谓词（``Callable[[int], bool]``）。
    :vartype status_code: int | Callable[[int], bool]
    :var media_type: 期望的 media type（如 ``application/octet-stream``），
        ``*`` 表示通配所有 media type。
    :vartype media_type: str
    :var adapter: Pydantic :class:`TypeAdapter` 实例，按 ``target_type`` 派发 bytes / str。
    :vartype adapter: TypeAdapter[T]

    Example::

        # 字节响应（如图片下载）。
        spec = RawResponseSpec(200, "image/png", bytes)
        result = response.expect(spec)  # → bytes

        # 文本响应（如纯文本接口）。
        spec = RawResponseSpec(200, "text/plain; charset=utf-8", str)
        result = response.expect(spec)  # → str
    """

    def __init__(
        self,
        status_code: int | Callable[[int], bool],
        media_type: str,
        target_type: type[T],
    ) -> None:
        """初始化原始响应协议。

        :param status_code: 期望的 HTTP 状态码（``int``）或状态码谓词（``Callable[[int], bool]``）。
        :param media_type: 期望的 media type（如 ``application/octet-stream``），
            ``*`` 表示通配所有 media type。
        :param target_type: 目标类型，必须是 ``bytes`` 或 ``str``。
        :raise TypeError: ``target_type`` 不是 ``bytes`` 或 ``str``（提示
            「必须 subscript ``RawResponseSpec[T]`` with bytes or str」）。
        """
        if target_type is not bytes and target_type is not str:
            msg = (
                f"RawResponseSpec 仅支持 bytes / str 类型参数，必须 subscript "
                f"RawResponseSpec[T] with bytes or str，得到 {target_type!r}"
            )
            raise TypeError(msg)
        super().__init__(status_code, media_type)
        self.adapter: TypeAdapter[T] = TypeAdapter(target_type)

    def validate_response(self, response: APIResponse) -> T:
        """校验并解析响应为 ``bytes`` 或 ``str``。

        流程：

        1. 调用 :meth:`_assert_status` 与 :meth:`_assert_media_type` 做协议级强校验。
        2. 调用 ``self.adapter.validate_python(response.body())``：Pydantic
           ``TypeAdapter`` 按 ``target_type`` 自动派发——``bytes`` 透传字节、
           ``str`` 按 UTF-8 解码。
        3. ``UnicodeDecodeError``（仅 ``target_type=str`` 时可能发生）包装为
           :class:`ParseError`，不向上透传原生异常。
           注意：Pydantic v2 在 bytes → str 强制转换失败时把
           ``UnicodeDecodeError`` 包装为自己的 ``ValidationError``（错误类型
           ``string_unicode``）而非直接抛出——此时也按 ``ParseError`` 透传，
           保证上层异常类型统一。

        :param response: Playwright 响应对象。
        :return: 已解析的响应内容，类型为 ``T``（``bytes`` 或 ``str``）。
        :raise AssertionError: status 或 content-type 与 spec 不匹配。
        :raise ParseError: ``T=str`` 时响应 body 非 UTF-8 编码。
        """
        self._assert_status(response.status)
        self._assert_media_type(response.headers.get("content-type", ""))

        try:
            return self.adapter.validate_python(response.body())
        except UnicodeDecodeError as e:
            msg = f"响应文本解码失败: {e}"
            raise ParseError(msg) from e
        except Exception as e:
            # Pydantic v2 在 bytes→str 转换失败时，把 UnicodeDecodeError 包装为
            # 自己的 ValidationError（type='string_unicode'），这里识别后透传为 ParseError。
            if hasattr(e, "errors"):
                for err in e.errors():
                    if err.get("type") == "string_unicode":
                        msg = f"响应文本解码失败: {err.get('msg', '')}"
                        raise ParseError(msg) from e
            raise


__all__ = ["Response", "BaseResponseSpec", "JSONResponseSpec", "RawResponseSpec"]
