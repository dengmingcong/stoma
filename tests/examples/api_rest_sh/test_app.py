"""tests/examples/api_rest_sh/test_app - 7 个匿名 e2e happy-path 场景。

覆盖 stoma ``Client.send()`` 的协议层与 schema 校验两个维度：

| # | HTTP | 请求体 | 响应 | Schema 校验 | 覆盖点 |
|---|------|--------|------|-------------|--------|
| 1 | GET    | 无          + query  | JSON    | 是 | query 字符串拼接 |
| 2 | POST   | JSON raw          | JSON    | 是 | raw body 编码 |
| 3 | POST   | urlencoded form   | JSON    | 是 | form 编码 |
| 4 | DELETE | 无          + path  | 204     | 否 | path 插值 + 204 短路 |
| 5 | OPTIONS| 无                | JSON    | 是 | OPTIONS 回显 |
| 6 | GET    | 无          + path  | octet-stream | 否 | 非 JSON 响应 |
| 7 | GET    | 无                | image/* | 否 | Accept content-negotiation |

所有场景均为 2xx，刻意避开已知 stoma 框架 bug 的边界（4xx 跳过 schema 校验 /
HEAD 空 body 解析 / 畸形 multipart spec）。
"""

from __future__ import annotations

from stoma.client import Client
from tests.examples.api_rest_sh.app.delete_book import DeleteBook
from tests.examples.api_rest_sh.app.get_accept_image import GetAcceptImage
from tests.examples.api_rest_sh.app.get_bytes import GetBytes
from tests.examples.api_rest_sh.app.get_method import GetMethod
from tests.examples.api_rest_sh.app.models import EchoModel, Method, TokenResponseBody
from tests.examples.api_rest_sh.app.options_method import OptionsMethod
from tests.examples.api_rest_sh.app.post_login import PostLogin
from tests.examples.api_rest_sh.app.post_method import PostMethod


def test_get_with_query_param_returns_validated(e2e_client: Client) -> None:
    """GET + query 参数：验证 query 拼接与 ``EchoModel`` schema 解析。

    ``status=200`` 作为 query 参数，由 ``_collect_query_params`` 收集后
    由 Playwright ``params=`` 拼接到 URL。
    """
    response = e2e_client.send(GetMethod(status=200))

    assert response.raw.status == 200
    assert response.validated is not None
    assert isinstance(response.validated, EchoModel)
    assert response.validated.method == Method.get
    assert response.validated.path == "/get"
    assert response.validated.url is not None
    assert "/get" in str(response.validated.url)


def test_post_raw_json_body_returns_validated(e2e_client: Client) -> None:
    """POST + raw JSON body：验证 raw 编码与 ``EchoModel`` schema 解析。

    ``PostMethod`` 无 body 字段 → ``RequestBodyKind.RAW`` 走空 body，
    服务器将请求回显为 ``EchoModel``。
    """
    response = e2e_client.send(PostMethod())

    assert response.raw.status == 200
    assert response.validated is not None
    assert isinstance(response.validated, EchoModel)
    assert response.validated.method == Method.post
    assert response.validated.path == "/post"


def test_post_form_urlencoded_body_returns_validated(e2e_client: Client) -> None:
    """POST + urlencoded form：验证 form 编码与 ``TokenResponseBody`` schema 解析。

    api.rest.sh 始终返回 ``user="anonymous"``（忽略输入 username），
    本断言只验证 schema 字段集与 token_type 枚举值，不强依赖回显。
    """
    response = e2e_client.send(PostLogin(username="alice"))

    assert response.raw.status == 200
    assert response.validated is not None
    assert isinstance(response.validated, TokenResponseBody)
    assert response.validated.user == "anonymous"
    assert response.validated.token_type.value == "Bearer"
    assert response.validated.token  # non-empty string from server


def test_delete_with_path_param_returns_204(e2e_client: Client) -> None:
    """DELETE + path 参数：验证 path 插值与 204 No Content 短路。

    204 路径在 ``build_response`` 中直接返回 ``validated=None``，
    调用方需通过 ``raw.status`` 判定成功。
    """
    response = e2e_client.send(DeleteBook(book_id="123"))

    assert response.raw.status == 204
    assert response.validated is None


def test_options_returns_validated(e2e_client: Client) -> None:
    """OPTIONS：验证 ``EchoModel`` schema 解析（method 应为 OPTIONS）。"""
    response = e2e_client.send(OptionsMethod())

    assert response.raw.status == 200
    assert response.validated is not None
    assert isinstance(response.validated, EchoModel)
    assert response.validated.method == Method.options
    assert response.validated.path == "/options"


def test_get_with_path_param_returns_octet_stream(e2e_client: Client) -> None:
    """GET + path 参数 + 非 JSON 响应：验证 path 插值与非 JSON 短路。

    ``content-type`` 不为 JSON 时 ``validated=None``，调用方通过 ``raw.body()``
    获取字节。
    """
    response = e2e_client.send(GetBytes(n=100))

    assert response.raw.status == 200
    assert response.validated is None
    content_type = response.raw.headers.get("content-type", "")
    assert "octet-stream" in content_type
    body = response.raw.body()
    assert len(body) >= 50


def test_get_accept_header_returns_image(e2e_client: Client) -> None:
    """GET + Accept content-negotiation + 非 JSON 响应：验证 content-type 协商。

    路径 ``/image`` 根据 Accept 头返回 ``image/*``，当 Accept 缺省时由
    OpenAPI operation 默认值兜底（具体策略由 codegen 决定）。
    """
    response = e2e_client.send(GetAcceptImage())

    assert response.raw.status == 200
    assert response.validated is None
    content_type = response.raw.headers.get("content-type", "")
    assert "image" in content_type
