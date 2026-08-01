"""T021 Integration Test: Client.send() 端到端测试

验证 User Story 2 的完整功能：
- 参数自动识别（Query/Path/Body/Header）
- HTTP 请求发送与响应解析（通过 Client）
- Response envelope（飞书风格）：raw + model
- 异常处理（HTTPError/ParseError/ValidationError）

使用 FastAPI mock server（`tests/integration/mock_app.py`）作为测试后端，
在后台线程通过 uvicorn 运行（`tests/integration/mock_server.py` 提供 fixture）。
"""

from typing import Annotated, Any

import pytest
from pydantic import BaseModel, Field

from src.client import Client
from src.params import Body, Path, Query
from src.routing import APIRoute, APIRouter


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
class GetUsers(APIRoute[list[UserData]]):
    """获取用户列表接口。"""

    limit: int = 20
    offset: int = 0


@router.get("/users/{user_id}")
class GetUserById(APIRoute[UserData]):
    """根据ID获取用户接口。"""

    user_id: Annotated[int, Path()]


@router.post("/users")
class CreateUser(APIRoute[UserData]):
    """创建用户接口。"""

    data: CreateUserRequest


@router.get("/items")
class GetItems(APIRoute[list[dict[str, Any]]]):
    """获取items接口，返回原始字典列表。"""

    category: str | None = None
    limit: Annotated[int, Query()] = Field(ge=1, le=100, default=10)


@router.post("/echo")
class EchoRequest(APIRoute[dict[str, Any]]):
    """回显接口，用于测试请求体。"""

    data: CreateUserRequest
    extra: str | None = None


@router.get("/text")
class GetText(APIRoute[dict[str, Any]]):
    """返回纯文本响应。"""


@router.get("/bytes")
class GetBytes(APIRoute[dict[str, Any]]):
    """返回二进制响应。"""


@router.get("/notype")
class GetNoType(APIRoute[dict[str, Any]]):
    """无 content-type 响应。"""


@router.get("/empty")
class GetEmpty(APIRoute[dict[str, Any]]):
    """空响应。"""


@router.get("/problem-json")
class GetProblemJson(APIRoute[dict[str, Any]]):
    """application/problem+json 响应。"""


@router.get("/server-error-json")
class GetServerErrorJson(APIRoute[dict[str, Any]]):
    """500 + JSON 响应。"""


@router.get("/server-error-text")
class GetServerErrorText(APIRoute[dict[str, Any]]):
    """500 + 文本响应。"""


@router.get("/charset-json")
class GetCharsetJson(APIRoute[dict[str, Any]]):
    """application/json; charset=utf-8 响应。"""


@router.get("/nonexistent")
class NonExistent(APIRoute[dict[str, Any]]):
    """404 响应测试端点。"""


# ===== Body Multiple Parameters 测试端点 =====


@router.post("/users-embed")
class CreateUserEmbed(APIRoute[dict[str, Any]]):
    """Body(embed=True) 测试：data 字段嵌入到顶层。"""

    data: Annotated[CreateUserRequest, Body(embed=True)]


@router.post("/importance")
class SetImportance(APIRoute[dict[str, Any]]):
    """标量 Body() 测试：importance 嵌入。"""

    importance: Annotated[int, Body()]


@router.post("/multi")
class CreateItemMulti(APIRoute[dict[str, Any]]):
    """多 body 测试：item + importance，每个独立命名。"""

    item: CreateUserRequest
    importance: Annotated[int, Body()]


@pytest.fixture
def api_context(mock_server: Any) -> Any:
    """创建 Playwright APIRequestContext（使用 mock_server 提供 base_url）。"""
    from playwright.sync_api import sync_playwright

    playwright = sync_playwright().start()
    context = playwright.request.new_context(base_url=mock_server.base_url)
    yield {"context": context, "base_url": mock_server.base_url, "playwright": playwright}
    context.dispose()
    playwright.stop()


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
        assert isinstance(response.data, list)
        assert len(response.data) == 20  # 默认 limit=20
        assert all(isinstance(u, UserData) for u in response.data)

    def test_get_users_list_with_params(self, client: Client) -> None:
        """测试 GET /users 带参数。"""

        endpoint = GetUsers(limit=5, offset=10)

        response = client.send(endpoint)

        assert response.raw.status == 200
        assert isinstance(response.data, list)
        assert len(response.data) == 5
        assert response.data[0].id == 10

    def test_get_user_by_id(self, client: Client) -> None:
        """测试 GET /users/{user_id} 路径参数。"""

        endpoint = GetUserById(user_id=42)

        response = client.send(endpoint)

        assert response.raw.status == 200
        assert isinstance(response.data, UserData)
        assert response.data.id == 42
        assert response.data.name == "User 42"
        assert response.data.email == "user42@example.com"

    def test_create_user(self, client: Client) -> None:
        """测试 POST /users 请求体。"""

        endpoint = CreateUser(data=CreateUserRequest(name="John Doe", email="john@example.com"))

        response = client.send(endpoint)

        assert response.raw.status == 201
        assert isinstance(response.data, UserData)
        assert response.data.id == 999
        assert response.data.name == "John Doe"
        assert response.data.email == "john@example.com"

    def test_query_params_filtering(self, client: Client) -> None:
        """测试查询参数过滤 None 值。"""

        endpoint = GetItems(category=None, limit=5)

        response = client.send(endpoint)

        assert response.raw.status == 200
        assert isinstance(response.data, list)
        assert len(response.data) == 5


class TestServersConfiguration:
    """servers 配置测试。"""

    def test_global_servers_config(self, client: Client) -> None:
        """测试全局 servers 配置（base_url 通过 context 设置）。"""
        endpoint = GetUsers()
        response = client.send(endpoint)

        assert response.raw.status == 200
        assert isinstance(response.data, list)
        assert len(response.data) == 20


class TestExceptionHandling:
    """异常处理测试。"""

    def test_returns_response_on_404(self, client: Client) -> None:
        """测试 HTTP 404 不抛错，而是返回 Response。

        4xx/5xx 仍会按 content-type 解析 body（这里是 JSON），所以 data 字段会填充。
        """
        endpoint = NonExistent()
        response = client.send(endpoint)

        assert response.raw.status == 404
        # T 是 dict[str, Any]，body 是 JSON，被解析为 dict
        assert response.data == {"error": "Not found"}

    def test_parse_error_on_invalid_json(self) -> None:
        """测试响应解析错误。

        注意：这个测试需要特殊设置的测试服务器返回无效 JSON。
        当前使用 Python 内置 http.server，它总是返回有效 JSON。
        """
        pytest.skip("需要特殊设置的测试 - 标准测试服务器总是返回有效 JSON")


class TestResponseEnvelope:
    """Response[T] 信封的集成测试。

    验证不同 content-type 下 Response 行为：
    - JSON：data 字段填充为 T 验证后的实例
    - text/binary：model = None，原始字节在 raw.content
    - HTTP 错误：不抛错，raw.status_code 反映状态
    """

    def test_json_success_200(self, client: Client) -> None:
        """JSON 成功：status 200, application/json → data 为 T 实例。"""

        endpoint = GetUserById(user_id=1)

        response = client.send(endpoint)

        assert response.raw.status == 200
        assert isinstance(response.data, UserData)
        assert response.data.id == 1

    def test_json_failure_500_returns_envelope(self, client: Client) -> None:
        """HTTP 500 + JSON body：返回 Response（不抛）。"""

        endpoint = GetServerErrorJson()

        response = client.send(endpoint)

        assert response.raw.status == 500
        # body 是 JSON，T 是 dict[str, Any]，会被验证为 dict
        assert response.data == {"error": "internal error"}

    def test_text_plain(self, client: Client) -> None:
        """纯文本：status 200, text/plain → model = None, raw.content 是 UTF-8 字节。"""

        endpoint = GetText()

        response = client.send(endpoint)

        assert response.raw.status == 200
        assert response.data is None  # 非 JSON，model 不填充
        assert response.raw.body() == b"hello world"

    def test_binary_octet_stream(self, client: Client) -> None:
        """二进制：status 200, application/octet-stream → model = None, raw.content 是字节。"""

        endpoint = GetBytes()

        response = client.send(endpoint)

        assert response.raw.status == 200
        assert response.data is None
        assert response.raw.body() == b"\x00\x01\x02\x03"

    def test_text_500(self, client: Client) -> None:
        """HTTP 500 + text body：返回 Response，model = None。"""

        endpoint = GetServerErrorText()

        response = client.send(endpoint)

        assert response.raw.status == 500
        assert response.data is None
        assert response.raw.body() == b"internal error"

    def test_no_content_type_fallback(self, client: Client) -> None:
        """无 content-type：model = None，原始字节在 raw.content。"""

        endpoint = GetNoType()

        response = client.send(endpoint)

        assert response.raw.status == 200
        assert response.data is None
        assert response.raw.body() == b"plain text body"

    def test_204_no_content(self, client: Client) -> None:
        """204 No Content：model = None，raw.content 为空。"""

        endpoint = GetEmpty()

        response = client.send(endpoint)

        assert response.raw.status == 204
        assert response.data is None
        assert response.raw.body() == b""

    def test_problem_json_plus_suffix(self, client: Client) -> None:
        """application/problem+json：走 JSON 路径（+json 后缀）。"""

        endpoint = GetProblemJson()

        response = client.send(endpoint)

        assert response.raw.status == 200
        assert response.data == {"detail": "everything is fine", "status": 200}

    def test_charset_in_content_type(self, client: Client) -> None:
        """application/json; charset=utf-8：strip charset 后走 JSON 路径。"""

        endpoint = GetCharsetJson()

        response = client.send(endpoint)

        assert response.raw.status == 200
        assert response.data == {"hello": "world"}

    def test_raw_response_has_status_code_and_headers(
        self, client: Client
    ) -> None:
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
        assert response.data is not None
        assert response.data.name == "Alice"
        assert response.data.email == "alice@example.com"

    def test_single_pydantic_body_embed_true(self, client: Client) -> None:
        """Body(embed=True) → data 字段嵌入到顶层：服务端从 data 子对象读取。"""

        endpoint = CreateUserEmbed(data=CreateUserRequest(name="Bob", email="bob@example.com"))

        response = client.send(endpoint)

        # 服务端从内嵌的 data 子对象提取，返回的是 dict
        assert response.raw.status == 201
        assert response.data is not None
        assert response.data["name"] == "Bob"
        assert response.data["email"] == "bob@example.com"

    def test_single_scalar_body_embedded(self, client: Client) -> None:
        """标量 Body() → 嵌入：服务端从 importance 键读取。"""

        endpoint = SetImportance(importance=42)

        response = client.send(endpoint)

        assert response.raw.status == 200
        assert response.data is not None
        assert response.data["received"] == 42

    def test_multiple_body_params_named(self, client: Client) -> None:
        """多 body 参数：item + importance，每个独立命名。"""

        endpoint = CreateItemMulti(
            item=CreateUserRequest(name="Charlie", email="charlie@example.com"),
            importance=99,
        )

        response = client.send(endpoint)

        assert response.raw.status == 200
        assert response.data is not None
        assert response.data["name"] == "Charlie"
        assert response.data["importance"] == 99


class TestClient:
    """Client 模式测试。

    验证：
    - `client.send(endpoint)` 返回 `Response[T]`，T 从 endpoint 推断
    - `client.dispose()` 释放 context
    - 链式 `client.send(endpoint).raw.status` 流畅
    """

    def test_send_returns_typed_response(self, client: Client) -> None:
        """client.send(endpoint) 返回 Response[T]，T 从 endpoint 推断。"""
        endpoint = GetUsers(limit=5)
        response = client.send(endpoint)

        # IDE 能推断 response.data 为 list[UserData] | None
        assert response.raw.status == 200
        assert isinstance(response.data, list)
        assert len(response.data) == 5

    def test_send_extracts_path_params(self, client: Client) -> None:
        """路径参数正确插值。"""
        endpoint = GetUserById(user_id=42)
        response = client.send(endpoint)

        assert response.raw.status == 200
        assert response.data.id == 42

    def test_send_builds_query_params(self, client: Client) -> None:
        """查询参数正确序列化。"""
        endpoint = GetUsers(limit=3, offset=10)
        response = client.send(endpoint)

        assert response.raw.status == 200
        assert len(response.data) == 3
        assert response.data[0].id == 10

    def test_send_body_preserves_pydantic_model(self, client: Client) -> None:
        """Pydantic model body 自动反序列化为 T 实例。"""
        endpoint = CreateUser(data=CreateUserRequest(name="Alice", email="a@x.com"))
        response = client.send(endpoint)

        assert response.raw.status == 201
        assert isinstance(response.data, UserData)
        assert response.data.name == "Alice"

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
        assert isinstance(create_response.data, UserData)
        user_id = create_response.data.id

        # 2. 获取用户
        get_endpoint = GetUserById(user_id=user_id)
        get_response = client.send(get_endpoint)
        assert get_response.raw.status == 200
        assert isinstance(get_response.data, UserData)
        # 注意：服务器返回的 name 是 "User {user_id}"，不是创建时传入的 name
        assert get_response.data.name == f"User {user_id}"

        # 3. 列出用户
        list_endpoint = GetUsers(limit=10)
        list_response = client.send(list_endpoint)
        assert list_response.raw.status == 200
        assert isinstance(list_response.data, list)
        assert len(list_response.data) <= 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
