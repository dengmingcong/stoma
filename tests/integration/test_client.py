"""T021 Integration Test: Client.send() 端到端测试

验证 User Story 2 的完整功能：
- 参数自动识别（Query/Path/Body/Header）
- HTTP 请求发送与响应解析（通过 Client）
- Response envelope（飞书风格）：raw + response.expect(spec) 显式触发协议校验
- 异常处理（HTTPError/ParseError/ValidationError）

使用 FastAPI mock server（`tests/integration/mock_app.py`）作为测试后端，
在后头线程通过 uvicorn 运行（`tests/integration/mock_server.py` 提供 fixture）。
"""

import pathlib
from typing import Annotated, Any

import pytest

pytest.importorskip("fastapi", reason="Mock server 测试需要 fastapi (stoma[test])")
from playwright.sync_api import Playwright
from pydantic import BaseModel, Field

from stoma import Body, Form, Header, Path, Query, ResponseSpec, UploadFile
from stoma.client import Client
from stoma.routing import APIRoute, APIRouter
from tests.integration.mock_server import _ServerThread


class UserData(BaseModel):
    """测试用的用户数据模型。"""

    id: int
    name: str
    email: str | None = None


class CreateUserRequest(BaseModel):
    """创建用户的请求体。"""

    name: str
    email: str


# 测试路由器
router = APIRouter()


@router.get("/users")
class GetUsers(APIRoute):
    """获取用户列表接口。"""

    limit: int = 20
    offset: int = 0

    @property
    def on_200(self) -> ResponseSpec[list[UserData]]:
        return ResponseSpec(status_code=200, media_type="application/json", expected_type=list[UserData])


@router.get("/users/{user_id}")
class GetUserById(APIRoute):
    """根据ID获取用户接口。"""

    user_id: Annotated[int, Path()]

    @property
    def on_200(self) -> ResponseSpec[UserData]:
        return ResponseSpec(status_code=200, media_type="application/json", expected_type=UserData)


@router.post("/users")
class CreateUser(APIRoute):
    """创建用户接口。"""

    data: CreateUserRequest

    @property
    def on_201(self) -> ResponseSpec[UserData]:
        return ResponseSpec(status_code=201, media_type="application/json", expected_type=UserData)


@router.get("/items")
class GetItems(APIRoute):
    """获取items接口，返回原始字典列表。"""

    category: str | None = None
    limit: Annotated[int, Query()] = Field(ge=1, le=100, default=10)

    @property
    def on_200(self) -> ResponseSpec[list[dict[str, Any]]]:
        return ResponseSpec(status_code=200, media_type="application/json", expected_type=list[dict[str, Any]])


@router.post("/echo")
class EchoRequest(APIRoute):
    """回显接口，用于测试请求体。"""

    data: CreateUserRequest
    extra: str | None = None

    @property
    def on_200(self) -> ResponseSpec[dict[str, Any]]:
        return ResponseSpec(status_code=200, media_type="application/json", expected_type=dict[str, Any])


@router.get("/text")
class GetText(APIRoute):
    """返回纯文本响应。"""

    @property
    def on_200(self) -> ResponseSpec[bytes]:
        return ResponseSpec(status_code=200, media_type="text/plain", expected_type=bytes)


@router.get("/bytes")
class GetBytes(APIRoute):
    """返回二进制响应。"""

    @property
    def on_200(self) -> ResponseSpec[bytes]:
        return ResponseSpec(status_code=200, media_type="application/octet-stream", expected_type=bytes)


@router.get("/notype")
class GetNoType(APIRoute):
    """无 content-type 响应。"""

    @property
    def on_200(self) -> ResponseSpec[bytes]:
        return ResponseSpec(status_code=200, media_type="*", expected_type=bytes)


@router.get("/empty")
class GetEmpty(APIRoute):
    """空响应。"""

    @property
    def on_204(self) -> ResponseSpec[bytes]:
        return ResponseSpec(status_code=204, media_type="*", expected_type=bytes)


@router.get("/problem-json")
class GetProblemJson(APIRoute):
    """application/problem+json 响应。"""

    @property
    def on_200(self) -> ResponseSpec[dict[str, Any]]:
        return ResponseSpec(status_code=200, media_type="application/problem+json", expected_type=dict[str, Any])


@router.get("/server-error-json")
class GetServerErrorJson(APIRoute):
    """500 + JSON 响应。"""

    @property
    def on_500(self) -> ResponseSpec[dict[str, Any]]:
        return ResponseSpec(status_code=500, media_type="application/json", expected_type=dict[str, Any])


@router.get("/server-error-text")
class GetServerErrorText(APIRoute):
    """500 + 文本响应。"""

    @property
    def on_500(self) -> ResponseSpec[bytes]:
        return ResponseSpec(status_code=500, media_type="text/plain", expected_type=bytes)


@router.get("/charset-json")
class GetCharsetJson(APIRoute):
    """application/json; charset=utf-8 响应。"""

    @property
    def on_200(self) -> ResponseSpec[dict[str, Any]]:
        return ResponseSpec(status_code=200, media_type="application/json", expected_type=dict[str, Any])


@router.get("/nonexistent")
class NonExistent(APIRoute):
    """404 响应测试端点。"""

    @property
    def on_404(self) -> ResponseSpec[dict[str, Any]]:
        return ResponseSpec(status_code=404, media_type="application/json", expected_type=dict[str, Any])


# ===== Body Multiple Parameters 测试端点 =====


@router.post("/users-embed")
class CreateUserEmbed(APIRoute):
    """Body(embed=True) 测试：data 字段嵌入到顶层。"""

    data: Annotated[CreateUserRequest, Body(embed=True)]

    @property
    def on_201(self) -> ResponseSpec[dict[str, Any]]:
        return ResponseSpec(status_code=201, media_type="application/json", expected_type=dict[str, Any])


@router.post("/importance")
class SetImportance(APIRoute):
    """标量 Body() 测试：importance 嵌入。"""

    importance: Annotated[int, Body(embed=True)]

    @property
    def on_200(self) -> ResponseSpec[dict[str, Any]]:
        return ResponseSpec(status_code=200, media_type="application/json", expected_type=dict[str, Any])


@router.post("/multi")
class CreateItemMulti(APIRoute):
    """多 body 测试：item + importance，每个独立命名。"""

    item: CreateUserRequest
    importance: Annotated[int, Body()]

    @property
    def on_200(self) -> ResponseSpec[dict[str, Any]]:
        return ResponseSpec(status_code=200, media_type="application/json", expected_type=dict[str, Any])


@router.post("/echo-headers")
class EchoHeadersRoute(APIRoute):
    """POST /echo-headers：Body(media_type=...) 设置 Content-Type 验证。"""

    value: Annotated[int, Body(media_type="text/plain")]

    @property
    def on_200(self) -> ResponseSpec[dict[str, str]]:
        return ResponseSpec(status_code=200, media_type="application/json", expected_type=dict[str, str])


@router.post("/echo-headers-override")
class EchoHeadersOverrideRoute(APIRoute):
    """POST /echo-headers-override：Header(Content-Type) 覆盖 Body(media_type)。

    同时声明 Body(media_type) 和 Header(Content-Type)，验证 caller header
    覆盖 Body 派生 Content-Type 的优先级。
    """

    value: Annotated[int, Body(media_type="text/plain")]
    content_type: Annotated[str, Header(), Field(serialization_alias="Content-Type")] = "application/x-custom"

    @property
    def on_200(self) -> ResponseSpec[dict[str, str]]:
        return ResponseSpec(status_code=200, media_type="application/json", expected_type=dict[str, str])


@router.post("/echo-body")
class StrBodyRoute(APIRoute):
    """POST /echo-body：``Annotated[str, Body(media_type="text/plain")]`` 字符串标量 body 验证。"""

    text: Annotated[str, Body(media_type="text/plain")]

    @property
    def on_200(self) -> ResponseSpec[dict[str, str]]:
        return ResponseSpec(status_code=200, media_type="application/json", expected_type=dict[str, str])


# ===== APIRoute 不带泛型参数测试端点 =====


@router.get("/health")
class HealthCheck(APIRoute):
    """健康检查端点，``on_200`` 声明响应协议。"""

    status: str = "ok"

    @property
    def on_200(self) -> ResponseSpec[dict[str, str]]:
        return ResponseSpec(status_code=200, media_type="application/json", expected_type=dict[str, str])


@router.head("/probe")
class ProbeHead(APIRoute):
    """HEAD /probe：HEAD 请求无 body，``on_200`` 用 ``*`` 通配 media type。"""

    @property
    def on_200(self) -> ResponseSpec[bytes]:
        return ResponseSpec(status_code=200, media_type="*", expected_type=bytes)


@router.options("/probe")
class ProbeOptions(APIRoute):
    """OPTIONS /probe：探测端点。"""

    @property
    def on_200(self) -> ResponseSpec[dict[str, str]]:
        return ResponseSpec(status_code=200, media_type="application/json", expected_type=dict[str, str])


@pytest.fixture
def api_context(
    mock_server: _ServerThread,
    _shared_playwright: Playwright,
) -> Any:
    """创建 Playwright APIRequestContext（使用 mock_server 提供 base_url）。

    复用顶层 ``tests/conftest.py`` 的会话级 ``_shared_playwright``，
    不在本地 ``sync_playwright().start()``，避免与其他 e2e/示例测试
    共存时产生 asyncio loop 状态污染。
    """
    context = _shared_playwright.request.new_context(base_url=mock_server.base_url)
    yield {"context": context, "base_url": mock_server.base_url, "playwright": _shared_playwright}
    context.dispose()


@pytest.fixture
def client(api_context: dict[str, Any]) -> Client:
    """提供共享的 Client 实例。"""
    return Client(context=api_context["context"])


class TestAPIRouteSend:
    """APIRoute.send() 方法集成测试。"""

    def test_get_users_list(self, client: Client) -> None:
        """测试 GET /users 列表接口。"""

        endpoint = GetUsers()
        response = client.send(endpoint)

        assert response.raw.status == 200
        users: list[UserData] = response.expect(endpoint.on_200)
        assert isinstance(users, list)
        assert len(users) == 20  # 默认 limit=20
        assert all(isinstance(u, UserData) for u in users)

    def test_get_users_list_with_params(self, client: Client) -> None:
        """测试 GET /users 带参数。"""

        endpoint = GetUsers(limit=5, offset=10)
        response = client.send(endpoint)

        assert response.raw.status == 200
        users: list[UserData] = response.expect(endpoint.on_200)
        assert isinstance(users, list)
        assert len(users) == 5
        assert users[0].id == 10

    def test_get_user_by_id(self, client: Client) -> None:
        """测试 GET /users/{user_id} 路径参数。"""

        endpoint = GetUserById(user_id=42)
        response = client.send(endpoint)

        assert response.raw.status == 200
        user: UserData = response.expect(endpoint.on_200)
        assert isinstance(user, UserData)
        assert user.id == 42
        assert user.name == "User 42"
        assert user.email == "user42@example.com"

    def test_create_user(self, client: Client) -> None:
        """测试 POST /users 请求体。"""

        endpoint = CreateUser(data=CreateUserRequest(name="John Doe", email="john@example.com"))
        response = client.send(endpoint)

        assert response.raw.status == 201
        created: UserData = response.expect(endpoint.on_201)
        assert isinstance(created, UserData)
        assert created.id == 999
        assert created.name == "John Doe"
        assert created.email == "john@example.com"

    def test_query_params_filtering(self, client: Client) -> None:
        """测试查询参数过滤 None 值。"""

        endpoint = GetItems(category=None, limit=5)
        response = client.send(endpoint)

        assert response.raw.status == 200
        items: list[dict[str, Any]] = response.expect(endpoint.on_200)
        assert isinstance(items, list)
        assert len(items) == 5


class TestServersConfiguration:
    """servers 配置测试。"""

    def test_global_servers_config(self, client: Client) -> None:
        """测试全局 servers 配置（base_url 通过 context 设置）。"""
        endpoint = GetUsers()
        response = client.send(endpoint)

        assert response.raw.status == 200
        users: list[UserData] = response.expect(endpoint.on_200)
        assert isinstance(users, list)
        assert len(users) == 20


class TestExceptionHandling:
    """异常处理测试。"""

    def test_returns_response_on_404(self, client: Client) -> None:
        """测试 HTTP 404 不抛错，而是返回 Response。

        4xx/5xx 仍会按 content-type 解析 body（这里是 JSON），所以 data 字段会填充。
        """
        endpoint = NonExistent()
        response = client.send(endpoint)

        assert response.raw.status == 404
        data: dict[str, Any] = response.expect(endpoint.on_404)
        assert data == {"error": "Not found"}

    def test_parse_error_on_invalid_json(self) -> None:
        """测试响应解析错误。

        注意：这个测试需要特殊设置的测试服务器返回无效 JSON。
        当前使用 Python 内置 http.server，它总是返回有效 JSON。
        """
        pytest.skip("需要特殊设置的测试 - 标准测试服务器总是返回有效 JSON")


class TestResponseEnvelope:
    """Response 信封的集成测试。

    验证不同 content-type 下 Response 行为：
    - JSON：通过 ``response.expect(spec)`` 解析为强类型 ``T`` 实例。
    - text/binary：通过 ``response.expect(spec)`` 解析为 ``bytes``。
    - HTTP 错误：``response.expect(spec)`` 仍按 status + content-type 解析 body。
    """

    def test_json_success_200(self, client: Client) -> None:
        """JSON 成功：status 200, application/json → expect 返回 ``UserData``。"""

        endpoint = GetUserById(user_id=1)
        response = client.send(endpoint)

        assert response.raw.status == 200
        user: UserData = response.expect(endpoint.on_200)
        assert isinstance(user, UserData)
        assert user.id == 1

    def test_json_failure_500_returns_envelope(self, client: Client) -> None:
        """HTTP 500 + JSON body：返回 Response（不抛）。"""

        endpoint = GetServerErrorJson()
        response = client.send(endpoint)

        assert response.raw.status == 500
        data: dict[str, Any] = response.expect(endpoint.on_500)
        assert data == {"error": "internal error"}

    def test_text_plain(self, client: Client) -> None:
        """纯文本：status 200, text/plain → ``response.expect`` 返回 ``bytes``。"""

        endpoint = GetText()
        response = client.send(endpoint)

        assert response.raw.status == 200
        body: bytes = response.expect(endpoint.on_200)
        assert body == b"hello world"

    def test_binary_octet_stream(self, client: Client) -> None:
        """二进制：status 200, application/octet-stream → ``response.expect`` 返回字节。"""

        endpoint = GetBytes()
        response = client.send(endpoint)

        assert response.raw.status == 200
        body: bytes = response.expect(endpoint.on_200)
        assert body == b"\x00\x01\x02\x03"

    def test_text_500(self, client: Client) -> None:
        """HTTP 500 + text body：返回 Response，``response.expect`` 返回字节。"""

        endpoint = GetServerErrorText()
        response = client.send(endpoint)

        assert response.raw.status == 500
        body: bytes = response.expect(endpoint.on_500)
        assert body == b"internal error"

    def test_no_content_type_fallback(self, client: Client) -> None:
        """无 content-type：``on_200`` 用 ``*`` 通配，``response.expect`` 返回字节。"""

        endpoint = GetNoType()
        response = client.send(endpoint)

        assert response.raw.status == 200
        body: bytes = response.expect(endpoint.on_200)
        assert body == b"plain text body"

    def test_204_no_content(self, client: Client) -> None:
        """204 No Content：``on_204`` 用 ``*`` 通配，``response.expect`` 返回空字节。"""

        endpoint = GetEmpty()
        response = client.send(endpoint)

        assert response.raw.status == 204
        body: bytes = response.expect(endpoint.on_204)
        assert body == b""

    def test_problem_json_plus_suffix(self, client: Client) -> None:
        """application/problem+json：``on_200`` 显式声明 ``media_type`` 精确匹配。"""

        endpoint = GetProblemJson()
        response = client.send(endpoint)

        assert response.raw.status == 200
        data: dict[str, Any] = response.expect(endpoint.on_200)
        assert data == {"detail": "everything is fine", "status": 200}

    def test_charset_in_content_type(self, client: Client) -> None:
        """application/json; charset=utf-8：strip charset 后走 JSON 路径。"""

        endpoint = GetCharsetJson()
        response = client.send(endpoint)

        assert response.raw.status == 200
        data: dict[str, Any] = response.expect(endpoint.on_200)
        assert data == {"hello": "world"}

    def test_raw_response_has_status_code_and_headers(self, client: Client) -> None:
        """RawResponse 包含 status_code 和 headers。"""

        endpoint = GetUserById(user_id=1)
        response = client.send(endpoint)

        assert response.raw.status == 200
        assert isinstance(response.raw.headers, dict)
        # Playwright 返回小写 header 名称
        assert "content-type" in response.raw.headers
        assert "application/json" in response.raw.headers["content-type"]


class TestBodyMultipleParams:
    """Body Multiple Parameters（FastAPI 兼容）集成测试。

    验证请求体序列化符合 FastAPI 规则：
    - 单 body Pydantic 模型自动识别 → 平展
    - Body(embed=True) → 嵌入
    - 标量 Body() → 嵌入
    - 多个 body 参数 → 每个独立命名
    """

    def test_single_pydantic_body_flat(self, client: Client) -> None:
        """单 body Pydantic 模型（CreateUser）→ 平展：服务端收到的是模型字段，不嵌入。

        复用 /users 端点（已存在的 CreateUser 接口）。
        """

        endpoint = CreateUser(data=CreateUserRequest(name="Alice", email="alice@example.com"))
        response = client.send(endpoint)

        # 服务端返回 201 表示请求体格式正确（平展）
        assert response.raw.status == 201
        created: UserData = response.expect(endpoint.on_201)
        assert created.name == "Alice"
        assert created.email == "alice@example.com"

    def test_single_pydantic_body_embed_true(self, client: Client) -> None:
        """Body(embed=True) → data 字段嵌入到顶层：服务端从 data 子对象读取。"""

        endpoint = CreateUserEmbed(data=CreateUserRequest(name="Bob", email="bob@example.com"))
        response = client.send(endpoint)

        # 服务端从内嵌的 data 子对象提取，返回的是 dict
        assert response.raw.status == 201
        data: dict[str, Any] = response.expect(endpoint.on_201)
        assert data["name"] == "Bob"
        assert data["email"] == "bob@example.com"

    def test_single_scalar_body_embedded(self, client: Client) -> None:
        """标量 Body() → 嵌入：服务端从 importance 键读取。"""

        endpoint = SetImportance(importance=42)
        response = client.send(endpoint)

        assert response.raw.status == 200
        data: dict[str, Any] = response.expect(endpoint.on_200)
        assert data["received"] == 42

    def test_multiple_body_params_named(self, client: Client) -> None:
        """多 body 参数：item + importance，每个独立命名。"""

        endpoint = CreateItemMulti(
            item=CreateUserRequest(name="Charlie", email="charlie@example.com"),
            importance=99,
        )
        response = client.send(endpoint)

        assert response.raw.status == 200
        data: dict[str, Any] = response.expect(endpoint.on_200)
        assert data["name"] == "Charlie"
        assert data["importance"] == 99


class TestMediaTypeIntegration:
    """Body(media_type=...) wire-level 集成测试。"""

    def test_body_media_type_sets_content_type_wire(self, client: Client) -> None:
        """Body(media_type="text/plain") → 服务端收到 text/plain Content-Type。"""

        endpoint = EchoHeadersRoute(value=42)
        response = client.send(endpoint)

        assert response.raw.status == 200
        data: dict[str, str] = response.expect(endpoint.on_200)
        assert "text/plain" in data["content_type"]

    def test_body_media_type_overridden_by_header(self, client: Client) -> None:
        """Header(alias="Content-Type") 覆盖 Body(media_type) 优先级。

        路由同时声明 ``Body(media_type="text/plain")`` 和 ``Header(Content-Type="application/x-custom")``，
        验证 wire 上服务端收到的是 caller header 的 Content-Type，而非 Body 派生的。
        """

        endpoint = EchoHeadersOverrideRoute(value=99)
        response = client.send(endpoint)

        assert response.raw.status == 200
        data: dict[str, str] = response.expect(endpoint.on_200)
        assert "application/x-custom" in data["content_type"]
        assert "text/plain" not in data["content_type"]


class TestStrBodyIntegration:
    """``Annotated[str, Body(media_type=...)]`` 字符串标量 body wire-level 集成测试。"""

    def test_str_scalar_body_received_by_server(self, client: Client) -> None:
        """``Annotated[str, Body(media_type="text/plain")]`` → 服务端收到裸字符串 + text/plain Content-Type。"""

        endpoint = StrBodyRoute(text="hello world 测试")
        response = client.send(endpoint)

        assert response.raw.status == 200
        data: dict[str, str] = response.expect(endpoint.on_200)
        assert data["body"] == "hello world 测试"
        assert "text/plain" in data["content_type"]


class TestClient:
    """Client 模式测试。

    验证：
    - `client.send(endpoint)` 返回 ``Response``，调用方按需 ``response.expect(spec)`` 触发协议校验。
    - `client.dispose()` 释放 context
    - 链式 `client.send(endpoint).raw.status` 流畅
    """

    def test_send_returns_typed_response(self, client: Client) -> None:
        """``client.send(endpoint)`` 返回 ``Response``，通过 ``response.expect(spec)`` 获得强类型数据。"""
        endpoint = GetUsers(limit=5)
        response = client.send(endpoint)

        assert response.raw.status == 200
        users: list[UserData] = response.expect(endpoint.on_200)
        assert isinstance(users, list)
        assert len(users) == 5

    def test_send_extracts_path_params(self, client: Client) -> None:
        """路径参数正确插值。"""
        endpoint = GetUserById(user_id=42)
        response = client.send(endpoint)

        assert response.raw.status == 200
        user: UserData = response.expect(endpoint.on_200)
        assert user.id == 42

    def test_send_builds_query_params(self, client: Client) -> None:
        """查询参数正确序列化。"""
        endpoint = GetUsers(limit=3, offset=10)
        response = client.send(endpoint)

        assert response.raw.status == 200
        users: list[UserData] = response.expect(endpoint.on_200)
        assert len(users) == 3
        assert users[0].id == 10

    def test_send_body_preserves_pydantic_model(self, client: Client) -> None:
        """Pydantic model body 自动反序列化为 T 实例。"""
        endpoint = CreateUser(data=CreateUserRequest(name="Alice", email="a@x.com"))
        response = client.send(endpoint)

        assert response.raw.status == 201
        created: UserData = response.expect(endpoint.on_201)
        assert isinstance(created, UserData)
        assert created.name == "Alice"

    def test_client_can_be_reused(self, client: Client) -> None:
        """Client 可复用，发送多个请求。"""
        endpoint1 = GetUsers(limit=1)
        endpoint2 = GetUserById(user_id=1)

        response1 = client.send(endpoint1)
        response2 = client.send(endpoint2)

        assert response1.raw.status == 200
        assert response2.raw.status == 200


class TestEndToEndFlow:
    """端到端流程测试。"""

    def test_complete_user_crud_flow(self, client: Client) -> None:
        """测试完整的用户 CRUD 流程。"""

        # 1. 创建用户
        create_endpoint = CreateUser(data=CreateUserRequest(name="Test User", email="test@example.com"))
        create_response = client.send(create_endpoint)
        assert create_response.raw.status == 201
        created: UserData = create_response.expect(create_endpoint.on_201)
        assert isinstance(created, UserData)
        user_id = created.id

        # 2. 获取用户
        get_endpoint = GetUserById(user_id=user_id)
        get_response = client.send(get_endpoint)
        assert get_response.raw.status == 200
        fetched: UserData = get_response.expect(get_endpoint.on_200)
        assert isinstance(fetched, UserData)
        # 注意：服务器返回的 name 是 "User {user_id}"，不是创建时传入的 name
        assert fetched.name == f"User {user_id}"

        # 3. 列出用户
        list_endpoint = GetUsers(limit=10)
        list_response = client.send(list_endpoint)
        assert list_response.raw.status == 200
        users: list[UserData] = list_response.expect(list_endpoint.on_200)
        assert isinstance(users, list)
        assert len(users) <= 10


class TestAPIRouteWithoutGeneric:
    """测试 APIRoute 通过 ``on_<status>`` @property 声明响应协议。"""

    def test_send_with_on_200(self, client: Client) -> None:
        """测试发送 APIRoute，通过 ``response.expect(on_200)`` 校验响应。

        ``response.expect`` 按 ``on_200`` 协议解析为强类型结果。
        """
        endpoint = HealthCheck(status="healthy")
        response = client.send(endpoint)

        # 状态码正确
        assert response.raw.status == 200
        data: dict[str, str] = response.expect(endpoint.on_200)
        assert data == {"status": "healthy"}
        # query 参数正确发送
        assert "status=healthy" in response.raw.url


class TestAllMethodsSend:
    """验证 HEAD/OPTIONS 方法的端到端发送。"""

    def test_head_e2e(self, client: Client) -> None:
        """验证 HEAD /probe 端到端发送。

        Starlette 对 HEAD 请求自动丢弃 body，只保留 headers。
        因此只验证 status code，不验证 body。
        """
        endpoint = ProbeHead()
        response = client.send(endpoint)

        assert response.raw.status == 200

    def test_options_e2e(self, client: Client) -> None:
        """验证 OPTIONS /probe 端到端发送。"""
        endpoint = ProbeOptions()
        response = client.send(endpoint)

        assert response.raw.status == 200
        data: dict[str, str] = response.expect(endpoint.on_200)
        assert data == {"method": "OPTIONS"}


# ===== Form / UploadFile / Mix Body 测试端点 =====


@router.post("/login")
class LoginRoute(APIRoute):
    """POST /login：多个标量 Form，端到端 urlencoded 序列化。"""

    username: Annotated[str, Form()]
    tags: Annotated[list[str], Form()]

    @property
    def on_200(self) -> ResponseSpec[dict[str, Any]]:
        return ResponseSpec(status_code=200, media_type="application/json", expected_type=dict[str, Any])


@router.post("/login-list")
class LoginListRoute(APIRoute):
    """POST /login-list：单个 ``Annotated[list[str], Form()]`` 标量列表。"""

    tags: Annotated[list[str], Form()]

    @property
    def on_200(self) -> ResponseSpec[dict[str, Any]]:
        return ResponseSpec(status_code=200, media_type="application/json", expected_type=dict[str, Any])


@router.post("/upload")
class UploadRoute(APIRoute):
    """POST /upload：单文件上传，验证 wire-level multipart 序列化。"""

    file: UploadFile

    @property
    def on_200(self) -> ResponseSpec[dict[str, Any]]:
        return ResponseSpec(status_code=200, media_type="application/json", expected_type=dict[str, Any])


@router.post("/upload-multi")
class UploadMultiRoute(APIRoute):
    """POST /upload-multi：多文件上传，验证 wire-level multipart 序列化。"""

    files: list[UploadFile]

    @property
    def on_200(self) -> ResponseSpec[dict[str, Any]]:
        return ResponseSpec(status_code=200, media_type="application/json", expected_type=dict[str, Any])


@router.post("/upload-mix")
class MixedFormFileRoute(APIRoute):
    """POST /upload-mix：标量 Form + UploadFile 共存，验证 wire-level multipart 序列化。"""

    username: Annotated[str, Form()]
    tags: Annotated[list[str], Form()]
    avatar: UploadFile

    @property
    def on_200(self) -> ResponseSpec[dict[str, Any]]:
        return ResponseSpec(status_code=200, media_type="application/json", expected_type=dict[str, Any])


@router.post("/upload-optional")
class UploadOptRoute(APIRoute):
    """POST /upload-optional：可选 ``UploadFile | None = None``。"""

    file: UploadFile | None = None

    @property
    def on_200(self) -> ResponseSpec[dict[str, Any]]:
        return ResponseSpec(status_code=200, media_type="application/json", expected_type=dict[str, Any])


@router.post("/upload-files-optional")
class UploadFilesOptRoute(APIRoute):
    """POST /upload-files-optional：可选 ``list[UploadFile] | None = None``。"""

    files: list[UploadFile] | None = None

    @property
    def on_200(self) -> ResponseSpec[dict[str, Any]]:
        return ResponseSpec(status_code=200, media_type="application/json", expected_type=dict[str, Any])


@router.post("/upload-raw", upload_as_multipart=False)
class UploadRawRoute(APIRoute):
    """POST /upload-raw：单文件 raw body 上传（整条 body 是文件内容）。"""

    file: UploadFile

    @property
    def on_200(self) -> ResponseSpec[dict[str, Any]]:
        return ResponseSpec(status_code=200, media_type="application/json", expected_type=dict[str, Any])


@router.post("/upload-raw", upload_as_multipart=False)
class UploadRawOptRoute(APIRoute):
    """POST /upload-raw-optional（路径复用 /upload-raw）：可选 UploadFile | None，未传时发空 body。

    路径复用 ``/upload-raw``（mock_app 仅一个 raw 端点）：
    - ``UploadRawRoute`` 提交文件字节 + Content-Type
    - ``UploadRawOptRoute()`` 提交空 body，Playwright 自动填 octet-stream
    """

    file: UploadFile | None = None

    @property
    def on_200(self) -> ResponseSpec[dict[str, Any]]:
        return ResponseSpec(status_code=200, media_type="application/json", expected_type=dict[str, Any])


@router.post("/upload-raw-override", upload_as_multipart=False)
class UploadRawOverrideRoute(APIRoute):
    """POST /upload-raw-override：单文件 raw body，APIRoute 显式声明 Content-Type。

    验证 APIRoute Header() 覆盖自动派生的 Content-Type（FilePayload.mimeType）。
    路径不复用 /upload-raw，避免影响原测试用例。
    """

    file: UploadFile
    content_type: Annotated[str, Header(), Field(serialization_alias="Content-Type")] = "application/x-custom"

    @property
    def on_200(self) -> ResponseSpec[dict[str, Any]]:
        return ResponseSpec(status_code=200, media_type="application/json", expected_type=dict[str, Any])


class TestFormBody:
    """Form 字段端到端测试。

    走真 HTTP（mock_server）：mock_app ``/login`` 用 ``Request`` 直接读 form，
    单值字段取原值、重复 key 合并为 ``list``。
    验证 stoma 的标量原值 + list 逐元素 ``append`` 序列化约定服务端能正确解析。
    """

    def test_form_urlencoded_login(self, client: Client) -> None:
        """多个标量 ``Form()`` → URLENCODED，e2e：list 字段成为重复 key。

        :param client: 共享的 Client 实例。
        """
        endpoint = LoginRoute(
            username="alice",
            tags=["vip", "beta"],
        )
        response = client.send(endpoint)

        assert response.raw.status == 200
        data: dict[str, Any] = response.expect(endpoint.on_200)
        assert data == {
            "username": "alice",
            "tags": ["vip", "beta"],
        }


class TestScalarFormList:
    """函数级 ``Annotated[list[str], Form()]`` 端到端测试。"""

    def test_scalar_list_urlencoded(self, client: Client) -> None:
        """标量列表 → urlencoded 重复 key，服务端 ``list[str] = Form()`` 解析为 list。

        :param client: 共享的 Client 实例。
        """
        endpoint = LoginListRoute(tags=["alpha", "beta", "gamma"])
        response = client.send(endpoint)

        assert response.raw.status == 200
        data: dict[str, Any] = response.expect(endpoint.on_200)
        assert data == {"tags": ["alpha", "beta", "gamma"]}


class TestUploadFileBody:
    """UploadFile 字段端到端测试。

    走真 HTTP（mock_server）：使用 Playwright ``FormData`` 序列化 multipart，
    验证服务端能正确接收并解析文件名、大小、内容类型。
    """

    def test_upload_single_file(self, client: Client, tmp_path: pathlib.Path) -> None:
        """单文件：上传到 ``/upload``，服务端返回 filename / size / content_type。

        :param client: 共享的 Client 实例。
        :param tmp_path: pytest 内置 tmp_path fixture，用于创建临时文件。
        """
        content = "hello world"
        file_path = tmp_path / "test.txt"
        file_path.write_text(content, encoding="utf-8")

        endpoint = UploadRoute(file=UploadFile(path=file_path))
        response = client.send(endpoint)

        assert response.raw.status == 200
        data: dict[str, Any] = response.expect(endpoint.on_200)
        assert data == {
            "filename": "test.txt",
            "size": len(content),
            "content_type": "text/plain",
        }

    def test_upload_multi_files(self, client: Client, tmp_path: pathlib.Path) -> None:
        """多文件：上传到 ``/upload-multi``，服务端返回 filenames 和 total_size。

        FormData 的 ``append`` 让同名 key 产生多个 part，对应 FastAPI ``list[UploadFile]``。

        :param client: 共享的 Client 实例。
        :param tmp_path: pytest 内置 tmp_path fixture，用于创建临时文件。
        """
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.md"
        file1.write_text("first file", encoding="utf-8")
        file2.write_text("second file content", encoding="utf-8")

        endpoint = UploadMultiRoute(
            files=[UploadFile(path=file1), UploadFile(path=file2)],
        )
        response = client.send(endpoint)

        assert response.raw.status == 200
        data: dict[str, Any] = response.expect(endpoint.on_200)
        assert data == {
            "filenames": ["file1.txt", "file2.md"],
            "total_size": len("first file") + len("second file content"),
        }


class TestMixedFormAndFile:
    """标量 Form + UploadFile 混合字段端到端测试。

    当存在文件字段时，整体走 multipart：标量 Form 字段原值、list 字段逐元素 ``append``
    后写入 ``FormData``。mock_app ``/upload-mix`` 用 ``Request`` 直接读 multipart，
    并对文件部分读取字节返回元信息。
    """

    def test_form_and_uploadfile_mix(self, client: Client, tmp_path: pathlib.Path) -> None:
        """Form + UploadFile 共存 → MULTIPART，e2e：服务端还原表单字段和文件元信息。

        :param client: 共享的 Client 实例。
        :param tmp_path: pytest 内置 tmp_path fixture，用于创建临时文件。
        """
        file_path = tmp_path / "avatar.png"
        file_path.write_bytes(b"\x89PNG\r\n\x1a\n")
        png_header_size = 8

        endpoint = MixedFormFileRoute(
            username="charlie",
            tags=["mix", "extra"],
            avatar=UploadFile(path=file_path),
        )
        response = client.send(endpoint)

        assert response.raw.status == 200
        data: dict[str, Any] = response.expect(endpoint.on_200)
        assert data == {
            "username": "charlie",
            "tags": ["mix", "extra"],
            "filename": "avatar.png",
            "size": png_header_size,
            "content_type": "image/png",
        }


class TestOptionalUploadFile:
    """``UploadFile | None`` / ``list[UploadFile] | None`` 端到端测试。

    验证可选文件字段在 stoma 客户端正确路由到 ``file_body_params``，
    ``None`` / 空列表时被跳过、文件存在时被序列化到 ``FormData``，
    对接 mock_app 的 ``/upload-optional`` / ``/upload-files-optional`` 端点。
    """

    def test_upload_opt_none(self, client: Client) -> None:
        """``file: UploadFile | None = None`` + ``file=None`` → 服务端收到 None 占位。

        :param client: 共享的 Client 实例。
        """
        endpoint = UploadOptRoute(file=None)
        response = client.send(endpoint)

        assert response.raw.status == 200
        data: dict[str, Any] = response.expect(endpoint.on_200)
        assert data == {"filename": None, "size": 0, "content_type": None}

    def test_upload_opt_missing(self, client: Client) -> None:
        """``file: UploadFile | None = None`` + 构造时不传 → 服务端收到 None 占位。

        :param client: 共享的 Client 实例。
        """
        endpoint = UploadOptRoute()  # 缺省值 None
        response = client.send(endpoint)

        assert response.raw.status == 200
        data: dict[str, Any] = response.expect(endpoint.on_200)
        assert data == {"filename": None, "size": 0, "content_type": None}

    def test_upload_opt_with_value(self, client: Client, tmp_path: pathlib.Path) -> None:
        """``file: UploadFile | None = None`` + ``file=UploadFile(...)`` → 服务端收到完整文件元信息。

        :param client: 共享的 Client 实例。
        :param tmp_path: pytest 内置 tmp_path fixture，用于创建临时文件。
        """
        content = "optional payload"
        file_path = tmp_path / "opt.txt"
        file_path.write_text(content, encoding="utf-8")

        endpoint = UploadOptRoute(file=UploadFile(path=file_path))
        response = client.send(endpoint)

        assert response.raw.status == 200
        data: dict[str, Any] = response.expect(endpoint.on_200)
        assert data == {
            "filename": "opt.txt",
            "size": len(content),
            "content_type": "text/plain",
        }

    def test_upload_files_opt_none(self, client: Client) -> None:
        """``files: list[UploadFile] | None = None`` + ``files=None`` → 服务端收到空列表占位。

        :param client: 共享的 Client 实例。
        """
        endpoint = UploadFilesOptRoute(files=None)
        response = client.send(endpoint)

        assert response.raw.status == 200
        data: dict[str, Any] = response.expect(endpoint.on_200)
        assert data == {"filenames": [], "total_size": 0}

    def test_upload_files_opt_with_value(self, client: Client, tmp_path: pathlib.Path) -> None:
        """``files: list[UploadFile] | None = None`` + ``files=[...]`` → 服务端收到完整文件列表。

        :param client: 共享的 Client 实例。
        :param tmp_path: pytest 内置 tmp_path fixture，用于创建临时文件。
        """
        file1 = tmp_path / "a.txt"
        file2 = tmp_path / "b.md"
        file1.write_text("first", encoding="utf-8")
        file2.write_text("second", encoding="utf-8")

        endpoint = UploadFilesOptRoute(files=[UploadFile(path=file1), UploadFile(path=file2)])
        response = client.send(endpoint)

        assert response.raw.status == 200
        data: dict[str, Any] = response.expect(endpoint.on_200)
        assert data == {
            "filenames": ["a.txt", "b.md"],
            "total_size": len("first") + len("second"),
        }


class TestRawUploadBody:
    """``upload_as_multipart=False`` 模式端到端测试。

    走真 HTTP（mock_server）：整条 body 是裸文件字节，Content-Type 来自
    ``mimetypes.guess_type(file_path)``。验证服务端能正确读出 size 和 content_type。
    """

    def test_raw_upload_pdf(self, client: Client, tmp_path: pathlib.Path) -> None:
        """``.pdf`` 文件 → 服务端收到 ``application/pdf`` 和实际字节数。

        :param client: 共享的 Client 实例。
        :param tmp_path: pytest 内置 tmp_path fixture，用于创建临时文件。
        """
        pdf = tmp_path / "doc.pdf"
        pdf_bytes = b"%PDF-1.4 fake content"
        pdf.write_bytes(pdf_bytes)
        endpoint = UploadRawRoute(file=UploadFile(path=pdf))

        response = client.send(endpoint)

        assert response.raw.status == 200
        data: dict[str, Any] = response.expect(endpoint.on_200)
        assert data == {"size": len(pdf_bytes), "content_type": "application/pdf"}

    def test_raw_upload_png(self, client: Client, tmp_path: pathlib.Path) -> None:
        """``.png`` 文件 → 服务端收到 ``image/png`` 和实际字节数。

        :param client: 共享的 Client 实例。
        :param tmp_path: pytest 内置 tmp_path fixture，用于创建临时文件。
        """
        png = tmp_path / "img.png"
        png_bytes = b"\x89PNG\r\n\x1a\n" + b"fake-ihdr-data"
        png.write_bytes(png_bytes)
        endpoint = UploadRawRoute(file=UploadFile(path=png))

        response = client.send(endpoint)

        assert response.raw.status == 200
        data: dict[str, Any] = response.expect(endpoint.on_200)
        assert data == {"size": len(png_bytes), "content_type": "image/png"}

    def test_raw_upload_txt(self, client: Client, tmp_path: pathlib.Path) -> None:
        """``.txt`` 文件 → 服务端收到 ``text/plain`` 和实际字节数。

        :param client: 共享的 Client 实例。
        :param tmp_path: pytest 内置 tmp_path fixture，用于创建临时文件。
        """
        txt = tmp_path / "note.txt"
        txt_bytes = b"Hello, raw world!"
        txt.write_bytes(txt_bytes)
        endpoint = UploadRawRoute(file=UploadFile(path=txt))

        response = client.send(endpoint)

        assert response.raw.status == 200
        data: dict[str, Any] = response.expect(endpoint.on_200)
        assert data == {"size": len(txt_bytes), "content_type": "text/plain"}

    def test_raw_upload_optional_none(self, client: Client) -> None:
        """``file: UploadFile = None`` + 不传 → 服务端收到 0 字节 + 空 content-type。

        value=None 时 client 发 ``b""`` 且不显式 set Content-Type，
        Playwright Node 端 :func:`fetch` 对空字节数据**不**自动填
        ``application/octet-stream``（实测验证），服务端读到的 content-type
        是空字符串。

        :param client: 共享的 Client 实例。
        """
        endpoint = UploadRawOptRoute()  # 缺省值 None

        response = client.send(endpoint)

        assert response.raw.status == 200
        data: dict[str, Any] = response.expect(endpoint.on_200)
        assert data == {"size": 0, "content_type": ""}

    def test_raw_upload_unknown_extension(self, client: Client, tmp_path: pathlib.Path) -> None:
        """``.unknownext`` 文件（``mimetypes.guess_type`` 返回 None）→ octet-stream fallback。

        与 ``.xyz`` 不同（stdlib 把 ``.xyz`` 映射成 ``chemical/x-xyz``，并非 None），
        ``.unknownext`` 保证 ``guess_type`` 返回 ``(None, None)``，验证兜底分支。

        :param client: 共享的 Client 实例。
        :param tmp_path: pytest 内置 tmp_path fixture，用于创建临时文件。
        """
        unknown = tmp_path / "data.unknownext"
        unknown_bytes = b"some random data"
        unknown.write_bytes(unknown_bytes)
        endpoint = UploadRawRoute(file=UploadFile(path=unknown))

        response = client.send(endpoint)

        assert response.raw.status == 200
        data: dict[str, Any] = response.expect(endpoint.on_200)
        assert data == {"size": len(unknown_bytes), "content_type": "application/octet-stream"}

    def test_raw_upload_apiroute_content_type_override(self, client: Client, tmp_path: pathlib.Path) -> None:
        """APIRoute 显式 ``Content-Type`` 覆盖自动派生的 mime。

        :param client: 共享的 Client 实例。
        :param tmp_path: pytest 内置 tmp_path fixture。
        """
        pdf = tmp_path / "doc.pdf"
        pdf_bytes = b"%PDF-1.4 fake content"
        pdf.write_bytes(pdf_bytes)
        endpoint = UploadRawOverrideRoute(file=UploadFile(path=pdf))

        response = client.send(endpoint)

        assert response.raw.status == 200
        data: dict[str, Any] = response.expect(endpoint.on_200)
        assert data == {
            "size": len(pdf_bytes),
            "content_type": "application/x-custom",
        }


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
