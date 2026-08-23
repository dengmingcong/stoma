"""tests/examples/api_rest_sh/test_app - 7 个匿名 e2e happy-path 场景。

覆盖 stoma ``Client.send()`` 的协议层与 schema 校验两个维度：

| # | HTTP | 请求体 | 响应 | Schema 校验 | 覆盖点 |
|---|------|--------|------|-------------|--------|
| 1 | GET    | 无          + query  | JSON    | 是 | query 字符串拼接 |
| 2 | POST   | JSON raw          | JSON    | 是 | raw body 编码 |
| 3 | POST   | urlencoded form   | JSON    | 是 | form 编码 |
| 4 | DELETE | 无          + path  | 204     | 否 | path 插值 + 204 短路 |
| 5 | OPTIONS| 无                | JSON    | 是 | OPTIONS 回显 |
| 6 | GET    | 无          + path  | octet-stream | 否 | 非 JSON 响应字节读取 |
| 7 | GET    | 无                | image/* | 否 | Accept content-negotiation |

所有场景均为 2xx，刻意避开已知 stoma 框架 bug 的边界（4xx 跳过 schema 校验 /
HEAD 空 body 解析 / 畸形 multipart spec）。

每个测试按需调用 ``response.expect(spec)`` 显式声明响应协议：

- JSON happy-path（场景 1/2/3/5）：用渲染器生成的 ``endpoint.on_200`` 属性，
  校验响应符合 OpenAPI 声明的 ``EchoModel`` / ``TokenResponseBody``。
- 204 / 非 JSON happy-path（场景 4/6/7）：spec 对这些端点的响应声明与实际
  服务器行为不一致（204 无 body 描述、``/bytes`` 与 ``/image`` 实际返回
  非 JSON 但 spec 仅声明 JSON），使用手工构造的 ``ResponseSpec``
  协议接收字节内容。

注意：渲染器生成的 ``on_<status>`` 是实例 ``@property``（不是 ``ClassVar``），
因此访问必须通过 ``endpoint`` 实例（如 ``endpoint.on_200``），不能直接通过类
（``GetMethod.on_200`` 会返回 property 描述符本身）。
"""

from __future__ import annotations

from stoma import ResponseSpec
from stoma.client import Client
from tests.examples.api_rest_sh.app.endpoints.delete_book import DeleteBook
from tests.examples.api_rest_sh.app.endpoints.get_accept_image import GetAcceptImage
from tests.examples.api_rest_sh.app.endpoints.get_bytes import GetBytes
from tests.examples.api_rest_sh.app.endpoints.get_method import GetMethod
from tests.examples.api_rest_sh.app.endpoints.options_method import OptionsMethod
from tests.examples.api_rest_sh.app.endpoints.post_login import PostLogin
from tests.examples.api_rest_sh.app.endpoints.post_method import PostMethod
from tests.examples.api_rest_sh.app.models import Method


def test_get_with_query_param_returns_validated(e2e_client: Client) -> None:
    """GET + query 参数：验证 query 拼接与 ``EchoModel`` schema 解析。

    ``status=200`` 作为 query 参数，由 ``_collect_query_params`` 收集后
    由 Playwright ``params=`` 拼接到 URL。
    """
    endpoint = GetMethod(status=200)
    response = e2e_client.send(endpoint)

    assert response.raw.status == 200
    data = response.expect(endpoint.on_200)
    assert data.method == Method.get
    assert data.path == "/get"
    assert data.url is not None
    assert "/get" in str(data.url)


def test_post_raw_json_body_returns_validated(e2e_client: Client) -> None:
    """POST + raw JSON body：验证 raw 编码与 ``EchoModel`` schema 解析。

    ``PostMethod`` 无 body 字段 → ``RequestBodyKind.RAW`` 走空 body，
    服务器将请求回显为 ``EchoModel``。
    """
    endpoint = PostMethod()
    response = e2e_client.send(endpoint)

    assert response.raw.status == 200
    data = response.expect(endpoint.on_200)
    assert data.method == Method.post
    assert data.path == "/post"


def test_post_form_urlencoded_body_returns_validated(e2e_client: Client) -> None:
    """POST + urlencoded form：验证 form 编码与 ``TokenResponseBody`` schema 解析。

    api.rest.sh 始终返回 ``user="anonymous"``（忽略输入 username），
    本断言只验证 schema 字段集与 token_type 枚举值，不强依赖回显。
    """
    endpoint = PostLogin(username="alice")
    response = e2e_client.send(endpoint)

    assert response.raw.status == 200
    data = response.expect(endpoint.on_200)
    assert data.user == "anonymous"
    assert data.token_type.value == "Bearer"
    assert data.token  # non-empty string from server


def test_delete_with_path_param_returns_204(e2e_client: Client) -> None:
    """DELETE + path 参数：验证 path 插值与 204 No Content 短路。

    spec 的 ``204`` 仅描述 ``"No Content"`` 无 body schema，渲染器仅发射
    ``on_default``（要求 ``application/problem+json``），与实际响应不符。
    用 ``ResponseSpec(204, "*", expected_type=bytes)`` 显式接收空字节。
    """
    endpoint = DeleteBook(book_id="123")
    response = e2e_client.send(endpoint)

    assert response.raw.status == 204
    body: bytes = response.expect(ResponseSpec(204, "*", expected_type=bytes))
    assert body == b""


def test_options_returns_validated(e2e_client: Client) -> None:
    """OPTIONS：验证 ``EchoModel`` schema 解析（method 应为 OPTIONS）。"""
    endpoint = OptionsMethod()
    response = e2e_client.send(endpoint)

    assert response.raw.status == 200
    data = response.expect(endpoint.on_200)
    assert data.method == Method.options
    assert data.path == "/options"


def test_get_with_path_param_returns_octet_stream(e2e_client: Client) -> None:
    """GET + path 参数 + 非 JSON 响应：验证 path 插值与非 JSON 字节读取。

    spec 的 ``/bytes/{n}`` 仅声明 ``application/json``（base64 string），
    实际服务器返回 ``application/octet-stream``。用
    ``ResponseSpec(200, "*", expected_type=bytes)`` 接收字节。
    """
    endpoint = GetBytes(n=100)
    response = e2e_client.send(endpoint)

    assert response.raw.status == 200
    body: bytes = response.expect(ResponseSpec(200, "*", expected_type=bytes))
    assert isinstance(body, bytes)
    assert len(body) >= 50
    content_type = response.raw.headers.get("content-type", "")
    assert "octet-stream" in content_type


def test_get_accept_header_returns_image(e2e_client: Client) -> None:
    """GET + Accept content-negotiation + 非 JSON 响应：验证 content-type 协商。

    路径 ``/image`` 根据 Accept 头返回 ``image/*``。spec 仅声明
    ``application/json``（base64 string），与实际响应不符。用
    ``ResponseSpec(200, "*", expected_type=bytes)`` 接收字节。
    """
    endpoint = GetAcceptImage()
    response = e2e_client.send(endpoint)

    assert response.raw.status == 200
    body: bytes = response.expect(ResponseSpec(200, "*", expected_type=bytes))
    assert isinstance(body, bytes)
    content_type = response.raw.headers.get("content-type", "")
    assert "image" in content_type
