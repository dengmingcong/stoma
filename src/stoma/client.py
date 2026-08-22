"""API Client，统一管理 Playwright context 和请求发送。

Client 是 stoma 的运行时入口，封装所有 HTTP 细节：

- 持有 Playwright APIRequestContext（用户提供）
- 调用 :func:`build_request` 从 APIRoute 提取参数
- 发送 HTTP 请求（通过 :meth:`Client._execute_request`）
- 调用 ``expect.validate_response`` 按响应协议校验并解析响应

调用模式：

    ctx = pw.request.new_context(base_url="http://localhost:8000")
    client = Client(context=ctx)
    response = client.send(GetUsers(limit=10), expect=GetUsers.on_200)
    # response: Response[T]，T 从 expect 推导

URL/Query 处理说明：

- base_url 由 Playwright context 管理（new_context 时设置）
- 查询参数通过 Playwright 的 ``params=dict`` 参数自动拼接为 query string
- 路径参数（{user_id}）由 :func:`build_request` 内的
  ``_interpolate_path_params`` 手动插值
- 路径只需相对路径（如 /users/123），Playwright 自动拼接 base_url
"""

from __future__ import annotations

from typing import Any

from playwright.sync_api import APIRequestContext, APIResponse

from stoma.dependencies.request import (
    Request,
    RequestBodyKind,
    build_request,
)
from stoma.dependencies.response import BaseResponseSpec, Response
from stoma.exceptions import HTTPError, ParseError, ValidationError
from stoma.routing import APIRoute


class Client:
    """API Client，统一管理 Playwright context。

    :param context: Playwright APIRequestContext 实例（由用户创建）。
    :type context: APIRequestContext

    Example::

        ctx = pw.request.new_context(
            base_url="http://localhost:8000",
            extra_http_headers={"Authorization": "Bearer xxx"},
        )
        client = Client(context=ctx)

        # endpoint 子类按状态码声明响应协议（``on_<status>``）。
        endpoint = GetUsers(limit=10)
        response = client.send(endpoint, expect=GetUsers.on_200)
        # IDE: response 类型为 Response[list[UserData]]，T 从 expect 推导
        # response.validated: list[UserData]
        # response.raw: Playwright APIResponse
    """

    def __init__(self, context: APIRequestContext) -> None:
        """初始化 Client。

        :param context: Playwright APIRequestContext 实例。
        :type context: APIRequestContext
        """
        self._context = context

    def send[T](self, api_route: APIRoute, expect: BaseResponseSpec[T]) -> Response[T]:
        """发送 api_route 请求，按 ``expect`` 协议校验响应并返回 :class:`Response[T]`。

        ``expect`` 是本次请求对应的响应协议（如 ``endpoint.on_200``），
        负责校验 HTTP 状态码与 media type 是否匹配，并按其 ``T``
        类型参数解析响应体。

        ``T`` 通过 PEP 695 泛型方法从 ``expect`` 的类型参数自动推断，
        与 ``api_route`` 无关（APIRoute 已不再携带泛型）。

        流程（全部内联在 :meth:`send` 内，无 helper）：

        1. 调用 :func:`build_request` 从 ``api_route`` 构造 :class:`Request`。
        2. 通过 :meth:`_execute_request` 发送 HTTP 请求，得到 ``api_response``。
        3. 调用 ``expect.validate_response(api_response)`` 校验状态码、media type、
           并按 ``T`` 解析响应体，得到 ``validated``。
        4. 返回 :class:`Response[T]`，``raw`` 持有原始 ``api_response``，
           ``validated`` 为已校验数据。

        :param api_route: APIRoute 实例。
        :param expect: 本次请求对应的响应协议（``BaseResponseSpec`` 子类实例），
            通常取 ``endpoint.on_<status>``。
        :return: 包装后的响应，类型为 :class:`Response[T]`。
        :raise HTTPError: 网络层失败时抛出。
        :raise ParseError: 响应体无法按协议解析（如 JSON 解码失败、文本解码失败）。
        :raise ValidationError: 响应解析成功但不符合 ``expect`` 的 ``T``。
        :raise AssertionError: 状态码或 content-type 与 ``expect`` 不匹配（协议违反），透传不包装。
        """
        try:
            request: Request = build_request(api_route)
            api_response = self._execute_request(request)
            validated = expect.validate_response(api_response)
            return Response[T](raw=api_response, validated=validated)
        except (HTTPError, ParseError, ValidationError, AssertionError):
            raise
        except Exception as e:
            msg = f"请求发送失败: {e}"
            raise HTTPError(msg) from e

    def dispose(self) -> None:
        """释放 Playwright context。"""
        self._context.dispose()

    def _execute_request(self, request: Request) -> APIResponse:
        """用 ``self._context`` 发送 HTTP 请求。

        统一通过 Playwright ``fetch`` 入口发送任意 HTTP 方法请求。
        Playwright 自动处理：

        - base_url 拼接（在 context 创建时设置）
        - query string 拼接（通过 params 参数）
        - 请求体编码（JSON 用 data，urlencoded 用 form，multipart 用 multipart）

        :param request: 由 :func:`src.dependencies.request.build_request` 构造的
            请求参数（method / path / params / headers / body）。
        :return: Playwright APIResponse 对象。
        :raise HTTPError: 网络层失败时抛出，消息包含 method/path 便于排错。
        """
        payload: dict[str, Any] = {}
        if request.body.kind is RequestBodyKind.MULTIPART_FORM:
            payload = {"multipart": request.body.form_data}
        elif request.body.kind is RequestBodyKind.URLENCODED_FORM:
            payload = {"form": request.body.form_data}
        elif request.body.kind is RequestBodyKind.BINARY:
            if request.body.binary_file is not None:
                payload = {"data": request.body.binary_file["buffer"]}
            # else: payload stays empty (no data, no Content-Type from binary_file).
        elif request.body.kind is RequestBodyKind.RAW:
            payload = {"data": request.body.raw_data.value if request.body.raw_data else None}
        else:
            msg = f"未知的 RequestBodyKind: {request.body.kind!r}"
            raise ValueError(msg)

        # 合并 headers：自动派生的 Content-Type + APIRoute 的 headers（APIRoute 优先——允许覆盖自动 mime）。
        derived_headers: dict[str, str] = {}
        if request.body.raw_data and request.body.raw_data.media_type:
            derived_headers["Content-Type"] = request.body.raw_data.media_type
        elif request.body.binary_file and request.body.binary_file.get("mimeType"):
            derived_headers["Content-Type"] = request.body.binary_file["mimeType"]
        merged_headers: dict[str, str] = {**derived_headers, **(request.headers or {})}

        try:
            return self._context.fetch(
                request.path,
                method=request.method,
                params=request.params if request.params else None,
                headers=merged_headers or None,
                **payload,
            )
        except Exception as e:
            msg = f"HTTP 请求失败 ({request.method} {request.path}): {e}"
            raise HTTPError(msg) from e
