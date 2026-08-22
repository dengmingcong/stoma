"""API 响应封装与协议类。

- :class:`Response` — 框架对外的统一响应包装（dataclass，泛型 ``T``）。
- :class:`BaseResponseSpec` — 响应协议抽象基类（泛型 ``T``），
  定义按 HTTP 状态码与 media type 严格校验响应的契约；
  :class:`JSONResponseSpec` / :class:`RawResponseSpec`
  为其具体实现，分别处理 JSON 与原始（``bytes`` / ``str``）两种响应，
  通过 :meth:`validate_response` 返回强类型的 ``T`` 实例。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, get_origin

from playwright.sync_api import APIResponse
from pydantic import TypeAdapter

from stoma.exceptions import ParseError, ValidationError


@dataclass
class Response[T]:
    """框架对外的统一响应包装。

    始终返回 :class:`Response`，不论 HTTP 状态码是否为错误。
    调用方通过 ``raw.status`` 判断请求成功/失败，
    并在响应协议期望的 content-type 上读取 ``validated``。

    ``Response`` 是 dataclass（而非 Pydantic BaseModel），
    因为 ``raw`` 字段持有 Playwright 的 :class:`APIResponse` 对象，该对象不是 Pydantic
    可识别的类型。使用 dataclass 既避免了 ``arbitrary_types_allowed`` 的额外配置，
    又保留了简洁的类型注解能力。

    设计要点：

    - ``raw``：Playwright 原始响应对象，类型为 ``playwright.sync_api.APIResponse``，
      提供完整 HTTP 协议层访问（``status`` / ``headers`` / ``text()`` / ``body()`` / ``json()``）。
    - ``validated``：由 :class:`BaseResponseSpec` 子类的
      :meth:`validate_response` 校验并解析为 ``T`` 类型后填充。

    :var raw: Playwright 原始响应对象。
    :vartype raw: APIResponse
    :var validated: 已校验并解析的响应数据，类型为 ``T``。
    :vartype validated: T

    Example::

        response = client.send(endpoint)
        if response.raw.status == 200:
            user = response.validated  # 类型为 UserData
        else:
            log.error(f"failed: {response.raw.status}")
    """

    raw: APIResponse
    validated: T


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
        status_code: int | Callable[[int], bool] | None = None,
        media_type: str | None = None,
        model: type[T] | None = None,
        *,
        callable: Callable[[int], bool] | None = None,
    ) -> None:
        """初始化 JSON 响应协议。

        :param status_code: 期望的 HTTP 状态码（``int``）或状态码谓词（``Callable[[int], bool]``）。
        :param media_type: 期望的 media type（如 ``application/json``），
            ``*`` 表示通配所有 media type。
        :param model: 用于校验响应 body 的 Pydantic 模型类。
        :param callable: 渲染器生成的 ``callable=`` 别名关键字，等价于 ``status_code=lambda ...``。
            ``status_code`` 与 ``callable`` 不能同时提供。
        :raise TypeError: ``status_code`` 与 ``callable`` 同时提供或都未提供；
            ``media_type`` / ``model`` 未提供。
        """
        if callable is not None:
            if status_code is not None:
                msg = "status_code 与 callable 不能同时提供"
                raise TypeError(msg)
            status_code = callable
        if status_code is None:
            msg = "必须提供 status_code 或 callable"
            raise TypeError(msg)
        if media_type is None:
            msg = "必须提供 media_type"
            raise TypeError(msg)
        if model is None:
            msg = "必须提供 model"
            raise TypeError(msg)
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


class RawResponseSpec[T](BaseResponseSpec[T]):
    """原始（``bytes`` / ``str``）响应协议。

    在 :class:`BaseResponseSpec` 的协议级强校验基础上，
    按类型参数 ``T`` 派发原始响应处理：

    - ``T = bytes`` → 返回 ``response.body()`` 的字节内容。
    - ``T = str`` → 返回 ``response.text()`` 的文本内容；编码失败时
      ``UnicodeDecodeError`` 被包装为 :class:`ParseError`。

    类型参数绑定机制：通过重写 :meth:`__class_getitem__` 让
    ``RawResponseSpec[bytes]`` 真正创建一个子类，并把 ``bytes``
    存到 ``type(self)._target_type``。默认 PEP 695 的下标
    仅返回 ``_GenericAlias``，实例化时拿不到具体类型参数，
    :meth:`validate_response` 无法按 ``T`` 分派。工厂方法
    :meth:`bytes` / :meth:`text` 是
    ``RawResponseSpec[bytes](...)`` / ``RawResponseSpec[str](...)``
    的语法糖，便于在不显式写泛型下标时使用。

    设计要点：

    - **类型参数必须显式提供**：裸 ``RawResponseSpec(...)``
      会在 :meth:`__init__` 抛 :class:`TypeError`；仅支持
      ``bytes`` 与 ``str``，其他类型参数在 :meth:`__class_getitem__`
      阶段就被拒绝（早失败）。
    - **强校验**：先走 :meth:`_assert_status` 与 :meth:`_assert_media_type`
      协议级检查；不通过抛 ``AssertionError``。
    - **裸字节路径** (``T=bytes``) ：``response.body()`` 不做解码，
      直接返回 bytes，适用于图片、protobuf、二进制下载等。
    - **文本路径** (``T=str``) ：``response.text()`` 默认 UTF-8 解码；
      非 UTF-8 内容抛 ``UnicodeDecodeError``，被包装为
      :class:`ParseError` 而非透传，统一上层异常类型。

    :var status_code: 期望的 HTTP 状态码（``int``）或状态码谓词（``Callable[[int], bool]``）。
    :vartype status_code: int | Callable[[int], bool]
    :var media_type: 期望的 media type（如 ``application/octet-stream``），
        ``*`` 表示通配所有 media type。
    :vartype media_type: str
    :var _target_type: 解析后的目标类型（``bytes`` 或 ``str``），
        由 :meth:`__class_getitem__` 在动态子类上绑定；
        裸 :class:`RawResponseSpec` 上未设置，:meth:`__init__` 会拒绝。
    :vartype _target_type: type | None

    Example::

        # 字节响应（如图片下载）。
        spec = RawResponseSpec.bytes(200, "image/png")
        result = spec.validate_response(response)  # → bytes

        # 文本响应（如纯文本接口）。
        spec = RawResponseSpec.text(200, "text/plain; charset=utf-8")
        result = spec.validate_response(response)  # → str
    """

    _target_type: type | None = None

    def __class_getitem__(cls, type_arg: Any) -> type:
        """为 :class:`RawResponseSpec` 绑定具体类型参数。

        重写默认 :meth:`object.__class_getitem__` 以真正创建一个子类，
        并把解析后的目标类型绑定到 ``type(self)._target_type``。
        默认 PEP 695 的下标仅返回 ``_GenericAlias``，实例化时
        拿不到具体类型参数，导致 :meth:`validate_response`
        无法按 ``T`` 分派。

        同时在创建前校验 ``type_arg``：必须是具体 ``type``，且必须是
        ``bytes`` 或 ``str``，否则抛 :class:`TypeError`，确保非法
        类型在下标阶段就被拒绝（早失败原则）。

        :param type_arg: 类型参数。
        :return: 以 ``type_arg`` 为 ``_target_type`` 的新子类。
        :raise TypeError: ``type_arg`` 不是 ``type`` 或不是 ``bytes``/``str``。
        """
        target = get_origin(type_arg) or type_arg
        if not isinstance(target, type):
            raise TypeError(f"RawResponseSpec[...] 类型参数必须是具体 type，得到 {type_arg!r}")
        if target is not bytes and target is not str:
            raise TypeError(f"RawResponseSpec 仅支持 bytes / str 类型参数，得到 {target!r}")
        arg_name = getattr(type_arg, "__name__", repr(type_arg))
        return type(f"RawResponseSpec[{arg_name}]", (cls,), {"_target_type": target})

    def __init__(
        self,
        status_code: int | Callable[[int], bool] | None = None,
        media_type: str | None = None,
        *,
        callable: Callable[[int], bool] | None = None,
    ) -> None:
        """初始化原始响应协议。

        要求 :attr:`_target_type` 已被 :meth:`__class_getitem__` 绑定，
        否则视为裸 :class:`RawResponseSpec` 调用而抛 :class:`TypeError`
        （PEP 695 风格必须显式提供类型参数）。

        :param status_code: 期望的 HTTP 状态码（``int``）或状态码谓词（``Callable[[int], bool]``）。
        :param media_type: 期望的 media type（如 ``application/octet-stream``），
            ``*`` 表示通配所有 media type。
        :param callable: 渲染器生成的 ``callable=`` 别名关键字，等价于 ``status_code=lambda ...``。
            ``status_code`` 与 ``callable`` 不能同时提供。
        :raise TypeError: 裸 :class:`RawResponseSpec` 调用未指定 ``T``；
            ``status_code`` 与 ``callable`` 同时提供或都未提供；``media_type`` 未提供。
        """
        if type(self)._target_type is None:
            raise TypeError(
                "RawResponseSpec 必须显式指定类型参数 T (bytes 或 str)；"
                "请使用 RawResponseSpec[bytes](...) / RawResponseSpec[str](...) "
                "或工厂方法 RawResponseSpec.bytes(...) / RawResponseSpec.text(...)。"
            )
        if callable is not None:
            if status_code is not None:
                msg = "status_code 与 callable 不能同时提供"
                raise TypeError(msg)
            status_code = callable
        if status_code is None:
            msg = "必须提供 status_code 或 callable"
            raise TypeError(msg)
        if media_type is None:
            msg = "必须提供 media_type"
            raise TypeError(msg)
        super().__init__(status_code, media_type)

    def validate_response(self, response: APIResponse) -> T:
        """校验并解析响应为 ``bytes`` 或 ``str``。

        流程：

        1. 从 ``response.headers`` 取 content-type，调用 :meth:`_assert_status`
           与 :meth:`_assert_media_type` 做协议级强校验。
        2. 按 :attr:`_target_type` 分派：

           - ``bytes`` → 返回 ``response.body()``（Playwright APIResponse 字节内容）。
           - ``str`` → 返回 ``response.text()``；UTF-8 解码失败（``UnicodeDecodeError``）
             被包装为 :class:`ParseError`。

        :param response: Playwright 响应对象。
        :return: 已解析的响应内容，类型为 ``bytes`` 或 ``str``。
        :raise AssertionError: status 或 content-type 与 spec 不匹配。
        :raise ParseError: ``T=str`` 时响应 body 非 UTF-8 编码。
        :raise TypeError: 内部 ``_target_type`` 既不是 ``bytes`` 也不是 ``str``
            （构造时已阻止，运行时仅为保险）。
        """
        content_type = response.headers.get("content-type", "") if response.headers else ""
        self._assert_status(response.status)
        self._assert_media_type(content_type)

        target = type(self)._target_type
        if target is bytes:
            return response.body()  # type: ignore[return-value]
        if target is str:
            try:
                return response.text()  # type: ignore[return-value]
            except UnicodeDecodeError as e:
                msg = f"响应文本解码失败: {e}"
                raise ParseError(msg) from e
        raise TypeError(f"RawResponseSpec 仅支持 bytes / str 类型参数，实际为 {target!r}")

    @classmethod
    def bytes(
        cls,
        status_code: int | Callable[[int], bool],
        media_type: str,
    ) -> RawResponseSpec[bytes]:
        """工厂方法：构造 ``RawResponseSpec[bytes]`` 实例。

        等价于 ``RawResponseSpec[bytes](status_code, media_type)``，
        仅省略类型参数下标，便于在 endpoint 声明中链式调用。

        :param status_code: 期望的 HTTP 状态码（``int``）或状态码谓词（``Callable[[int], bool]``）。
        :param media_type: 期望的 media type（如 ``application/octet-stream``），
            ``*`` 表示通配所有 media type。
        :return: ``RawResponseSpec[bytes]`` 实例（``T`` 自动绑定为 ``bytes``）。
        """
        return RawResponseSpec[bytes](status_code, media_type)

    @classmethod
    def text(
        cls,
        status_code: int | Callable[[int], bool],
        media_type: str,
    ) -> RawResponseSpec[str]:
        """工厂方法：构造 ``RawResponseSpec[str]`` 实例。

        等价于 ``RawResponseSpec[str](status_code, media_type)``，
        仅省略类型参数下标，便于在 endpoint 声明中链式调用。

        :param status_code: 期望的 HTTP 状态码（``int``）或状态码谓词（``Callable[[int], bool]``）。
        :param media_type: 期望的 media type（如 ``text/plain``），
            ``*`` 表示通配所有 media type。
        :return: ``RawResponseSpec[str]`` 实例（``T`` 自动绑定为 ``str``）。
        """
        return RawResponseSpec[str](status_code, media_type)


__all__ = ["Response", "BaseResponseSpec", "JSONResponseSpec", "RawResponseSpec"]
