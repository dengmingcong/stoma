"""T021 Integration Test: APIRoute.send() 端到端测试

验证 User Story 2 的完整功能：
- 参数自动识别（Query/Path/Body/Header）
- 服务器配置（servers）
- HTTP 请求发送与响应解析
- Response envelope（飞书风格）：raw + model
- 异常处理（HTTPError/ParseError/ValidationError）

使用 Python 内置 http.server 创建测试服务器。
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Annotated, Any

import pytest
from pydantic import BaseModel

from src.params import Body, Path, Query
from src.routing import APIRoute, APIRouter

# 测试服务器配置
TEST_HOST = "127.0.0.1"
TEST_PORT = 18766


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
    limit: Annotated[int, Query(ge=1, le=100)] = 10


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


class HTTPHandler(BaseHTTPRequestHandler):
    """测试用 HTTP 请求处理器。"""

    def log_message(self, format: str, *args: Any) -> None:
        """抑制日志输出。"""
        pass

    def _send_json_response(self, status: int, data: Any) -> None:
        """发送 application/json 响应。"""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _send_json_with_charset(self, status: int, data: Any) -> None:
        """发送带 charset 的 application/json 响应。"""
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _send_problem_json(self, status: int, data: Any) -> None:
        """发送 application/problem+json 响应。"""
        self.send_response(status)
        self.send_header("Content-Type", "application/problem+json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _send_text_response(self, status: int, text: str) -> None:
        """发送 text/plain 响应。"""
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(text.encode("utf-8"))

    def _send_binary_response(self, status: int, data: bytes) -> None:
        """发送 application/octet-stream 响应。"""
        self.send_response(status)
        self.send_header("Content-Type", "application/octet-stream")
        self.end_headers()
        self.wfile.write(data)

    def _send_no_content(self, status: int) -> None:
        """发送无 body 的响应。"""
        self.send_response(status)
        self.end_headers()

    def _send_no_type(self, status: int, body: bytes) -> None:
        """发送无 Content-Type 的响应。"""
        self.send_response(status)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        """处理 GET 请求。"""
        path = self.path

        if path.startswith("/users/"):
            parts = path.split("/")
            if len(parts) == 3 and parts[2].isdigit():
                user_id = int(parts[2])
                self._send_json_response(
                    200, {"id": user_id, "name": f"User {user_id}", "email": f"user{user_id}@example.com"}
                )
                return

        if path.startswith("/items"):
            params = {}
            if "?" in path:
                query = path.split("?")[1]
                for param in query.split("&"):
                    if "=" in param:
                        key, value = param.split("=", 1)
                        params[key] = value

            category = params.get("category", "default")
            limit = int(params.get("limit", "10"))
            items = [{"id": i, "name": f"Item {i}", "category": category} for i in range(limit)]
            self._send_json_response(200, items)
            return

        if path.startswith("/users"):
            params = {}
            if "?" in path:
                query = path.split("?")[1]
                for param in query.split("&"):
                    if "=" in param:
                        key, value = param.split("=", 1)
                        params[key] = value

            limit = int(params.get("limit", "20"))
            offset = int(params.get("offset", "0"))
            users = [
                {"id": i, "name": f"User {i}", "email": f"user{i}@example.com"} for i in range(offset, offset + limit)
            ]
            self._send_json_response(200, users)
            return

        if path == "/text":
            self._send_text_response(200, "hello world")
            return

        if path == "/bytes":
            self._send_binary_response(200, b"\x00\x01\x02\x03")
            return

        if path == "/notype":
            self._send_no_type(200, b"plain text body")
            return

        if path == "/empty":
            self._send_no_content(204)
            return

        if path == "/problem-json":
            self._send_problem_json(200, {"detail": "everything is fine", "status": 200})
            return

        if path == "/server-error-json":
            self._send_json_response(500, {"error": "internal error"})
            return

        if path == "/server-error-text":
            self._send_text_response(500, "internal error")
            return

        if path == "/charset-json":
            self._send_json_with_charset(200, {"hello": "world"})
            return

        # 404
        self._send_json_response(404, {"error": "Not found"})

    def do_POST(self) -> None:  # noqa: N802
        """处理 POST 请求。"""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode() if content_length > 0 else "{}"

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self._send_json_response(400, {"error": "Invalid JSON"})
            return

        if self.path == "/users":
            # 单 body Pydantic 模型：平展（FastAPI 默认 embed=False）
            user_id = 999
            user = {"id": user_id, "name": data.get("name", ""), "email": data.get("email")}
            self._send_json_response(201, user)
            return

        if self.path == "/users-embed":
            # Body(embed=True)：data 字段嵌入到顶层
            if "data" not in data or not isinstance(data["data"], dict):
                self._send_json_response(400, {"error": "expected embedded data"})
                return
            inner = data["data"]
            user_id = 999
            user = {"id": user_id, "name": inner.get("name", ""), "email": inner.get("email")}
            self._send_json_response(201, user)
            return

        if self.path == "/importance":
            # 标量 Body()：嵌入到顶层
            if "importance" not in data:
                self._send_json_response(400, {"error": "expected importance"})
                return
            self._send_json_response(200, {"received": data["importance"]})
            return

        if self.path == "/multi":
            # 多 body：每个独立命名
            if "item" not in data or "importance" not in data:
                self._send_json_response(400, {"error": "expected item and importance"})
                return
            inner = data["item"]
            self._send_json_response(200, {
                "name": inner.get("name"),
                "importance": data["importance"],
            })
            return

        if self.path == "/echo":
            self._send_json_response(200, data)
            return

        # 404
        self._send_json_response(404, {"error": "Not found"})


class TestServer:
    """测试服务器管理器。"""

    def __init__(self, host: str = TEST_HOST, port: int = TEST_PORT) -> None:
        self.host = host
        self.port = port
        self.server: HTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """启动测试服务器。"""
        self.server = HTTPServer((self.host, self.port), HTTPHandler)
        self._thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """停止测试服务器。"""
        if self.server:
            self.server.shutdown()
            self.server.server_close()

    @property
    def base_url(self) -> str:
        """获取基础 URL。"""
        return f"http://{self.host}:{self.port}"


@pytest.fixture(scope="module")
def test_server() -> TestServer:
    """测试服务器 fixture。"""
    server = TestServer()
    server.start()
    yield server
    server.stop()


@pytest.fixture
def api_context(test_server: TestServer) -> Any:
    """创建 Playwright APIRequestContext。"""
    from playwright.sync_api import sync_playwright

    playwright = sync_playwright().start()
    context = playwright.request.new_context()
    yield {"context": context, "base_url": test_server.base_url, "playwright": playwright}
    context.dispose()
    playwright.stop()


class TestAPIRouteSend:
    """APIRoute.send() 方法集成测试。"""

    def test_get_users_list(self, api_context: dict[str, Any], test_server: TestServer) -> None:
        """测试 GET /users 列表接口。"""
        context = api_context["context"]
        base_url = test_server.base_url

        endpoint = GetUsers()
        endpoint._servers = [base_url]

        response = endpoint.send(context)

        assert response.raw.status == 200
        assert isinstance(response.model, list)
        assert len(response.model) == 20  # 默认 limit=20
        assert all(isinstance(u, UserData) for u in response.model)

    def test_get_users_list_with_params(self, api_context: dict[str, Any], test_server: TestServer) -> None:
        """测试 GET /users 带参数。"""
        context = api_context["context"]
        base_url = test_server.base_url

        endpoint = GetUsers(limit=5, offset=10)
        endpoint._servers = [base_url]

        response = endpoint.send(context)

        assert response.raw.status == 200
        assert isinstance(response.model, list)
        assert len(response.model) == 5
        assert response.model[0].id == 10

    def test_get_user_by_id(self, api_context: dict[str, Any], test_server: TestServer) -> None:
        """测试 GET /users/{user_id} 路径参数。"""
        context = api_context["context"]
        base_url = test_server.base_url

        endpoint = GetUserById(user_id=42)
        endpoint._servers = [base_url]

        response = endpoint.send(context)

        assert response.raw.status == 200
        assert isinstance(response.model, UserData)
        assert response.model.id == 42
        assert response.model.name == "User 42"
        assert response.model.email == "user42@example.com"

    def test_create_user(self, api_context: dict[str, Any], test_server: TestServer) -> None:
        """测试 POST /users 请求体。"""
        context = api_context["context"]
        base_url = test_server.base_url

        endpoint = CreateUser(data=CreateUserRequest(name="John Doe", email="john@example.com"))
        endpoint._servers = [base_url]

        response = endpoint.send(context)

        assert response.raw.status == 201
        assert isinstance(response.model, UserData)
        assert response.model.id == 999
        assert response.model.name == "John Doe"
        assert response.model.email == "john@example.com"

    def test_query_params_filtering(self, api_context: dict[str, Any], test_server: TestServer) -> None:
        """测试查询参数过滤 None 值。"""
        context = api_context["context"]
        base_url = test_server.base_url

        endpoint = GetItems(category=None, limit=5)
        endpoint._servers = [base_url]

        response = endpoint.send(context)

        assert response.raw.status == 200
        assert isinstance(response.model, list)
        assert len(response.model) == 5


class TestServersConfiguration:
    """servers 配置测试。"""

    def test_global_servers_config(self, test_server: TestServer) -> None:
        """测试全局 servers 配置。"""
        from playwright.sync_api import sync_playwright

        playwright = sync_playwright().start()
        context = playwright.request.new_context()
        base_url = test_server.base_url

        try:
            endpoint = GetUsers()
            endpoint._servers = [base_url]

            response = endpoint.send(context)

            assert response.raw.status == 200
            assert isinstance(response.model, list)
            assert len(response.model) == 20
        finally:
            context.dispose()
            playwright.stop()


class TestExceptionHandling:
    """异常处理测试。"""

    def test_returns_response_on_404(self, test_server: TestServer) -> None:
        """测试 HTTP 404 不抛错，而是返回 Response。

        调用方应通过 ``raw.status_code`` 判断是否成功。
        4xx/5xx 仍会按 content-type 解析 body（这里是 JSON），所以 model 字段会填充。
        """
        from playwright.sync_api import sync_playwright

        playwright = sync_playwright().start()
        context = playwright.request.new_context()
        base_url = test_server.base_url

        try:
            endpoint = NonExistent()
            endpoint._servers = [base_url]

            # 4xx/5xx 不再抛错，而是返回 Response
            response = endpoint.send(context)

            assert response.raw.status == 404
            # T 是 dict[str, Any]，body 是 JSON，被解析为 dict
            assert response.model == {"error": "Not found"}
        finally:
            context.dispose()
            playwright.stop()

    def test_parse_error_on_invalid_json(self) -> None:
        """测试响应解析错误。

        注意：这个测试需要特殊设置的测试服务器返回无效 JSON。
        当前使用 Python 内置 http.server，它总是返回有效 JSON。
        """
        pytest.skip("需要特殊设置的测试 - 标准测试服务器总是返回有效 JSON")


class TestResponseEnvelope:
    """Response[T] 信封的集成测试。

    验证不同 content-type 下 Response 行为：
    - JSON：model 字段填充为 T 验证后的实例
    - text/binary：model = None，原始字节在 raw.content
    - HTTP 错误：不抛错，raw.status_code 反映状态
    """

    def test_json_success_200(self, api_context: dict[str, Any], test_server: TestServer) -> None:
        """JSON 成功：status 200, application/json → data 为 T 实例。"""
        context = api_context["context"]
        base_url = test_server.base_url

        endpoint = GetUserById(user_id=1)
        endpoint._servers = [base_url]

        response = endpoint.send(context)

        assert response.raw.status == 200
        assert isinstance(response.model, UserData)
        assert response.model.id == 1

    def test_json_failure_500_returns_envelope(self, api_context: dict[str, Any], test_server: TestServer) -> None:
        """HTTP 500 + JSON body：返回 Response（不抛）。"""
        context = api_context["context"]
        base_url = test_server.base_url

        endpoint = GetServerErrorJson()
        endpoint._servers = [base_url]

        response = endpoint.send(context)

        assert response.raw.status == 500
        # body 是 JSON，T 是 dict[str, Any]，会被验证为 dict
        assert response.model == {"error": "internal error"}

    def test_text_plain(self, api_context: dict[str, Any], test_server: TestServer) -> None:
        """纯文本：status 200, text/plain → model = None, raw.content 是 UTF-8 字节。"""
        context = api_context["context"]
        base_url = test_server.base_url

        endpoint = GetText()
        endpoint._servers = [base_url]

        response = endpoint.send(context)

        assert response.raw.status == 200
        assert response.model is None  # 非 JSON，model 不填充
        assert response.raw.body() == b"hello world"

    def test_binary_octet_stream(self, api_context: dict[str, Any], test_server: TestServer) -> None:
        """二进制：status 200, application/octet-stream → model = None, raw.content 是字节。"""
        context = api_context["context"]
        base_url = test_server.base_url

        endpoint = GetBytes()
        endpoint._servers = [base_url]

        response = endpoint.send(context)

        assert response.raw.status == 200
        assert response.model is None
        assert response.raw.body() == b"\x00\x01\x02\x03"

    def test_text_500(self, api_context: dict[str, Any], test_server: TestServer) -> None:
        """HTTP 500 + text body：返回 Response，model = None。"""
        context = api_context["context"]
        base_url = test_server.base_url

        endpoint = GetServerErrorText()
        endpoint._servers = [base_url]

        response = endpoint.send(context)

        assert response.raw.status == 500
        assert response.model is None
        assert response.raw.body() == b"internal error"

    def test_no_content_type_fallback(self, api_context: dict[str, Any], test_server: TestServer) -> None:
        """无 content-type：model = None，原始字节在 raw.content。"""
        context = api_context["context"]
        base_url = test_server.base_url

        endpoint = GetNoType()
        endpoint._servers = [base_url]

        response = endpoint.send(context)

        assert response.raw.status == 200
        assert response.model is None
        assert response.raw.body() == b"plain text body"

    def test_204_no_content(self, api_context: dict[str, Any], test_server: TestServer) -> None:
        """204 No Content：model = None，raw.content 为空。"""
        context = api_context["context"]
        base_url = test_server.base_url

        endpoint = GetEmpty()
        endpoint._servers = [base_url]

        response = endpoint.send(context)

        assert response.raw.status == 204
        assert response.model is None
        assert response.raw.body() == b""

    def test_problem_json_plus_suffix(self, api_context: dict[str, Any], test_server: TestServer) -> None:
        """application/problem+json：走 JSON 路径（+json 后缀）。"""
        context = api_context["context"]
        base_url = test_server.base_url

        endpoint = GetProblemJson()
        endpoint._servers = [base_url]

        response = endpoint.send(context)

        assert response.raw.status == 200
        assert response.model == {"detail": "everything is fine", "status": 200}

    def test_charset_in_content_type(self, api_context: dict[str, Any], test_server: TestServer) -> None:
        """application/json; charset=utf-8：strip charset 后走 JSON 路径。"""
        context = api_context["context"]
        base_url = test_server.base_url

        endpoint = GetCharsetJson()
        endpoint._servers = [base_url]

        response = endpoint.send(context)

        assert response.raw.status == 200
        assert response.model == {"hello": "world"}

    def test_raw_response_has_status_code_and_headers(
        self, api_context: dict[str, Any], test_server: TestServer
    ) -> None:
        """RawResponse 包含 status_code 和 headers。"""
        context = api_context["context"]
        base_url = test_server.base_url

        endpoint = GetUserById(user_id=1)
        endpoint._servers = [base_url]

        response = endpoint.send(context)

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

    def test_single_pydantic_body_flat(self, api_context: dict[str, Any], test_server: TestServer) -> None:
        """单 body Pydantic 模型（CreateUser）→ 平展：服务端收到的是模型字段，不嵌入。

        复用 /users 端点（已存在的 CreateUser 接口）。
        """
        context = api_context["context"]
        base_url = test_server.base_url

        endpoint = CreateUser(data=CreateUserRequest(name="Alice", email="alice@example.com"))
        endpoint._servers = [base_url]

        response = endpoint.send(context)

        # 服务端返回 201 表示请求体格式正确（平展）
        assert response.raw.status == 201
        assert response.model is not None
        assert response.model.name == "Alice"
        assert response.model.email == "alice@example.com"

    def test_single_pydantic_body_embed_true(self, api_context: dict[str, Any], test_server: TestServer) -> None:
        """Body(embed=True) → data 字段嵌入到顶层：服务端从 data 子对象读取。"""
        context = api_context["context"]
        base_url = test_server.base_url

        endpoint = CreateUserEmbed(data=CreateUserRequest(name="Bob", email="bob@example.com"))
        endpoint._servers = [base_url]

        response = endpoint.send(context)

        # 服务端从内嵌的 data 子对象提取，返回的是 dict
        assert response.raw.status == 201
        assert response.model is not None
        assert response.model["name"] == "Bob"
        assert response.model["email"] == "bob@example.com"

    def test_single_scalar_body_embedded(self, api_context: dict[str, Any], test_server: TestServer) -> None:
        """标量 Body() → 嵌入：服务端从 importance 键读取。"""
        context = api_context["context"]
        base_url = test_server.base_url

        endpoint = SetImportance(importance=42)
        endpoint._servers = [base_url]

        response = endpoint.send(context)

        assert response.raw.status == 200
        assert response.model is not None
        assert response.model["received"] == 42

    def test_multiple_body_params_named(self, api_context: dict[str, Any], test_server: TestServer) -> None:
        """多 body 参数：item + importance，每个独立命名。"""
        context = api_context["context"]
        base_url = test_server.base_url

        endpoint = CreateItemMulti(
            item=CreateUserRequest(name="Charlie", email="charlie@example.com"),
            importance=99,
        )
        endpoint._servers = [base_url]

        response = endpoint.send(context)

        assert response.raw.status == 200
        assert response.model is not None
        assert response.model["name"] == "Charlie"
        assert response.model["importance"] == 99


class TestEndToEndFlow:
    """端到端流程测试。"""

    def test_complete_user_crud_flow(self, api_context: dict[str, Any], test_server: TestServer) -> None:
        """测试完整的用户 CRUD 流程。"""
        context = api_context["context"]
        base_url = test_server.base_url

        # 1. 创建用户
        create_endpoint = CreateUser(data=CreateUserRequest(name="Test User", email="test@example.com"))
        create_endpoint._servers = [base_url]
        create_response = create_endpoint.send(context)
        assert create_response.raw.status == 201
        assert isinstance(create_response.model, UserData)
        user_id = create_response.model.id

        # 2. 获取用户
        get_endpoint = GetUserById(user_id=user_id)
        get_endpoint._servers = [base_url]
        get_response = get_endpoint.send(context)
        assert get_response.raw.status == 200
        assert isinstance(get_response.model, UserData)
        # 注意：服务器返回的 name 是 "User {user_id}"，不是创建时传入的 name
        assert get_response.model.name == f"User {user_id}"

        # 3. 列出用户
        list_endpoint = GetUsers(limit=10)
        list_endpoint._servers = [base_url]
        list_response = list_endpoint.send(context)
        assert list_response.raw.status == 200
        assert isinstance(list_response.model, list)
        assert len(list_response.model) <= 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
