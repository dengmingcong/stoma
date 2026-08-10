"""T021 Integration Test: Client.send() 端到端测试

验证 User Story 2 的完整功能：
- 参数自动识别（Query/Path/Body/Header）
- HTTP 请求发送与响应解析（通过 Client）
- Response envelope（飞书风格）：raw + model
- 异常处理（HTTPError/ParseError/ValidationError）

使用 FastAPI mock server（`tests/integration/mock_app.py`）作为测试后端，
在后台线程通过 uvicorn 运行（`tests/integration/mock_server.py` 提供 fixture）。
"""

import pathlib
from typing import Annotated, Any

import pytest
from playwright.sync_api import FormData
from pydantic import BaseModel, Field

from src.client import Client, RequestBodyKind
from src.params import Body, Form, Path, Query, UploadFile
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


# ===== APIRoute 不带泛型参数测试端点 =====


@router.get("/health")
class HealthCheck(APIRoute):
    """健康检查端点，不校验响应。"""

    status: str = "ok"


@router.head("/probe")
class ProbeHead(APIRoute[dict[str, str]]):
    pass


@router.options("/probe")
class ProbeOptions(APIRoute[dict[str, str]]):
    pass


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
        assert isinstance(response.validated, list)
        assert len(response.validated) == 20  # 默认 limit=20
        assert all(isinstance(u, UserData) for u in response.validated)

    def test_get_users_list_with_params(self, client: Client) -> None:
        """测试 GET /users 带参数。"""

        endpoint = GetUsers(limit=5, offset=10)

        response = client.send(endpoint)

        assert response.raw.status == 200
        assert isinstance(response.validated, list)
        assert len(response.validated) == 5
        assert response.validated[0].id == 10

    def test_get_user_by_id(self, client: Client) -> None:
        """测试 GET /users/{user_id} 路径参数。"""

        endpoint = GetUserById(user_id=42)

        response = client.send(endpoint)

        assert response.raw.status == 200
        assert isinstance(response.validated, UserData)
        assert response.validated.id == 42
        assert response.validated.name == "User 42"
        assert response.validated.email == "user42@example.com"

    def test_create_user(self, client: Client) -> None:
        """测试 POST /users 请求体。"""

        endpoint = CreateUser(data=CreateUserRequest(name="John Doe", email="john@example.com"))

        response = client.send(endpoint)

        assert response.raw.status == 201
        assert isinstance(response.validated, UserData)
        assert response.validated.id == 999
        assert response.validated.name == "John Doe"
        assert response.validated.email == "john@example.com"

    def test_query_params_filtering(self, client: Client) -> None:
        """测试查询参数过滤 None 值。"""

        endpoint = GetItems(category=None, limit=5)

        response = client.send(endpoint)

        assert response.raw.status == 200
        assert isinstance(response.validated, list)
        assert len(response.validated) == 5


class TestServersConfiguration:
    """servers 配置测试。"""

    def test_global_servers_config(self, client: Client) -> None:
        """测试全局 servers 配置（base_url 通过 context 设置）。"""
        endpoint = GetUsers()
        response = client.send(endpoint)

        assert response.raw.status == 200
        assert isinstance(response.validated, list)
        assert len(response.validated) == 20


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
        assert response.validated == {"error": "Not found"}

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
        assert isinstance(response.validated, UserData)
        assert response.validated.id == 1

    def test_json_failure_500_returns_envelope(self, client: Client) -> None:
        """HTTP 500 + JSON body：返回 Response（不抛）。"""

        endpoint = GetServerErrorJson()

        response = client.send(endpoint)

        assert response.raw.status == 500
        # body 是 JSON，T 是 dict[str, Any]，会被验证为 dict
        assert response.validated == {"error": "internal error"}

    def test_text_plain(self, client: Client) -> None:
        """纯文本：status 200, text/plain → model = None, raw.content 是 UTF-8 字节。"""

        endpoint = GetText()

        response = client.send(endpoint)

        assert response.raw.status == 200
        assert response.validated is None  # 非 JSON，model 不填充
        assert response.raw.body() == b"hello world"

    def test_binary_octet_stream(self, client: Client) -> None:
        """二进制：status 200, application/octet-stream → model = None, raw.content 是字节。"""

        endpoint = GetBytes()

        response = client.send(endpoint)

        assert response.raw.status == 200
        assert response.validated is None
        assert response.raw.body() == b"\x00\x01\x02\x03"

    def test_text_500(self, client: Client) -> None:
        """HTTP 500 + text body：返回 Response，model = None。"""

        endpoint = GetServerErrorText()

        response = client.send(endpoint)

        assert response.raw.status == 500
        assert response.validated is None
        assert response.raw.body() == b"internal error"

    def test_no_content_type_fallback(self, client: Client) -> None:
        """无 content-type：model = None，原始字节在 raw.content。"""

        endpoint = GetNoType()

        response = client.send(endpoint)

        assert response.raw.status == 200
        assert response.validated is None
        assert response.raw.body() == b"plain text body"

    def test_204_no_content(self, client: Client) -> None:
        """204 No Content：model = None，raw.content 为空。"""

        endpoint = GetEmpty()

        response = client.send(endpoint)

        assert response.raw.status == 204
        assert response.validated is None
        assert response.raw.body() == b""

    def test_problem_json_plus_suffix(self, client: Client) -> None:
        """application/problem+json：走 JSON 路径（+json 后缀）。"""

        endpoint = GetProblemJson()

        response = client.send(endpoint)

        assert response.raw.status == 200
        assert response.validated == {"detail": "everything is fine", "status": 200}

    def test_charset_in_content_type(self, client: Client) -> None:
        """application/json; charset=utf-8：strip charset 后走 JSON 路径。"""

        endpoint = GetCharsetJson()

        response = client.send(endpoint)

        assert response.raw.status == 200
        assert response.validated == {"hello": "world"}

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
        assert response.validated is not None
        assert response.validated.name == "Alice"
        assert response.validated.email == "alice@example.com"

    def test_single_pydantic_body_embed_true(self, client: Client) -> None:
        """Body(embed=True) → data 字段嵌入到顶层：服务端从 data 子对象读取。"""

        endpoint = CreateUserEmbed(data=CreateUserRequest(name="Bob", email="bob@example.com"))

        response = client.send(endpoint)

        # 服务端从内嵌的 data 子对象提取，返回的是 dict
        assert response.raw.status == 201
        assert response.validated is not None
        assert response.validated["name"] == "Bob"
        assert response.validated["email"] == "bob@example.com"

    def test_single_scalar_body_embedded(self, client: Client) -> None:
        """标量 Body() → 嵌入：服务端从 importance 键读取。"""

        endpoint = SetImportance(importance=42)

        response = client.send(endpoint)

        assert response.raw.status == 200
        assert response.validated is not None
        assert response.validated["received"] == 42

    def test_multiple_body_params_named(self, client: Client) -> None:
        """多 body 参数：item + importance，每个独立命名。"""

        endpoint = CreateItemMulti(
            item=CreateUserRequest(name="Charlie", email="charlie@example.com"),
            importance=99,
        )

        response = client.send(endpoint)

        assert response.raw.status == 200
        assert response.validated is not None
        assert response.validated["name"] == "Charlie"
        assert response.validated["importance"] == 99


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

        # IDE 能推断 response.validated 为 list[UserData] | None
        assert response.raw.status == 200
        assert isinstance(response.validated, list)
        assert len(response.validated) == 5

    def test_send_extracts_path_params(self, client: Client) -> None:
        """路径参数正确插值。"""
        endpoint = GetUserById(user_id=42)
        response = client.send(endpoint)

        assert response.raw.status == 200
        assert response.validated
        assert response.validated.id == 42

    def test_send_builds_query_params(self, client: Client) -> None:
        """查询参数正确序列化。"""
        endpoint = GetUsers(limit=3, offset=10)
        response = client.send(endpoint)

        assert response.raw.status == 200
        assert response.validated
        assert len(response.validated) == 3
        assert response.validated[0].id == 10

    def test_send_body_preserves_pydantic_model(self, client: Client) -> None:
        """Pydantic model body 自动反序列化为 T 实例。"""
        endpoint = CreateUser(data=CreateUserRequest(name="Alice", email="a@x.com"))
        response = client.send(endpoint)

        assert response.raw.status == 201
        assert isinstance(response.validated, UserData)
        assert response.validated.name == "Alice"

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
        assert isinstance(create_response.validated, UserData)
        user_id = create_response.validated.id

        # 2. 获取用户
        get_endpoint = GetUserById(user_id=user_id)
        get_response = client.send(get_endpoint)
        assert get_response.raw.status == 200
        assert isinstance(get_response.validated, UserData)
        # 注意：服务器返回的 name 是 "User {user_id}"，不是创建时传入的 name
        assert get_response.validated.name == f"User {user_id}"

        # 3. 列出用户
        list_endpoint = GetUsers(limit=10)
        list_response = client.send(list_endpoint)
        assert list_response.raw.status == 200
        assert isinstance(list_response.validated, list)
        assert len(list_response.validated) <= 10


class TestAPIRouteWithoutGeneric:
    """测试 APIRoute 不带泛型参数。"""

    def test_send_without_generic(self, client: Client) -> None:
        """测试发送不带泛型参数的 APIRoute。

        不校验响应，validated 始终为 None。
        """
        endpoint = HealthCheck(status="healthy")
        response = client.send(endpoint)

        # 状态码正确
        assert response.raw.status == 200
        # 不校验响应，validated 始终为 None
        assert response.validated is None
        # query 参数正确发送
        assert "status=healthy" in response.raw.url

    def test_dependant_has_no_response_schema(self) -> None:
        """验证 _get_dependant 中 json_response_schema 为 None。"""
        dependant = HealthCheck._get_dependant()
        assert dependant.json_response_schema is None
        assert dependant.json_response_schema_adapter is None
        # 参数收集正常
        assert dependant.method == "GET"
        assert dependant.path == "/health"
        assert len(dependant.query_params) == 1
        assert dependant.query_params[0].name == "status"


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
        assert response.validated == {"method": "OPTIONS"}


# ===== Form / UploadFile / Mix Body 测试端点 =====


class _LoginForm(BaseModel):
    """Form 测试用登录表单（BaseModel + Form 平展）。"""

    username: str
    tags: list[str]
    prefs: dict[str, str]


@router.post("/login")
class LoginRoute(APIRoute[dict[str, Any]]):
    """POST /login：单字段 Form，验证 wire-level urlencoded 序列化。"""

    username: Annotated[str, Form()]
    tags: Annotated[list[str], Form()]
    prefs: Annotated[dict, Form()]


@router.post("/login-flat")
class LoginFlatRoute(APIRoute[dict[str, Any]]):
    """POST /login-flat：BaseModel + Form（embed=False 默认）子字段平展。"""

    data: Annotated[_LoginForm, Form()]


@router.post("/upload")
class UploadRoute(APIRoute[dict[str, Any]]):
    """POST /upload：单文件上传，验证 wire-level multipart 序列化。"""

    file: UploadFile


@router.post("/upload-multi")
class UploadMultiRoute(APIRoute[dict[str, Any]]):
    """POST /upload-multi：多文件上传，验证 wire-level multipart 序列化。"""

    files: list[UploadFile]


@router.post("/upload-mix")
class MixedFormFileRoute(APIRoute[dict[str, Any]]):
    """POST /upload-mix：Form + UploadFile 共存，验证 wire-level multipart 序列化。"""

    data: Annotated[_LoginForm, Form()]
    avatar: UploadFile


@router.post("/upload-optional")
class UploadOptRoute(APIRoute[dict[str, Any]]):
    """POST /upload-optional：可选 ``UploadFile | None = None``。"""

    file: UploadFile | None = None


@router.post("/upload-files-optional")
class UploadFilesOptRoute(APIRoute[dict[str, Any]]):
    """POST /upload-files-optional：可选 ``list[UploadFile] | None = None``。"""

    files: list[UploadFile] | None = None


class TestFormBody:
    """Form 字段 wire-level 测试。

    注：mock_app /login 的 list/dict Form 字段与 Playwright ``form=`` 序列化存在
    不兼容性（FastAPI 无法解析 stoma 生成的 JSON 编码字符串，会返回 422），
    因此本测试类只做 wire-level 验证（``_serialize_body_params``），
    不做端到端真实 HTTP。
    """

    def test_form_urlencoded_login(self, client: Client) -> None:
        """单字段 Form() → URLENCODED，标量原值、列表/字典走 ``json.dumps``。

        :param client: 共享的 Client 实例。
        """
        endpoint = LoginRoute(
            username="alice",
            tags=["vip", "beta"],
            prefs={"theme": "dark", "lang": "en"},
        )

        body = client._serialize_body_params(endpoint, endpoint._get_dependant())

        assert body.kind is RequestBodyKind.URLENCODED
        assert body.form_data is not None
        assert isinstance(body.form_data, FormData)
        # str 标量原值存储，与 FastAPI Form() 直接接收字符串一致
        assert body.form_data._fields[0] == ("username", "alice")
        # list[str] 走 json.dumps → JSON 字符串（带空格）
        assert body.form_data._fields[1] == ("tags", '["vip", "beta"]')
        # dict 走 json.dumps → JSON 字符串
        assert body.form_data._fields[2] == ("prefs", '{"theme": "dark", "lang": "en"}')

    def test_form_basemodel_embed_false(self, client: Client) -> None:
        """BaseModel + Form()（embed=False 默认）→ 子字段平展在 form_data 顶层。

        标量子字段原值，集合子字段（list/dict）走 ``json.dumps``。

        :param client: 共享的 Client 实例。
        """
        endpoint = LoginFlatRoute(
            data=_LoginForm(
                username="bob",
                tags=["admin"],
                prefs={"theme": "light"},
            ),
        )

        body = client._serialize_body_params(endpoint, endpoint._get_dependant())

        assert body.kind is RequestBodyKind.URLENCODED
        assert body.form_data is not None
        assert isinstance(body.form_data, FormData)
        # embed=False 平展：BaseModel 子字段在 form_data 顶层。
        # 平展字段名是 BaseModel 的 field_name，不是 alias。
        # 标量子字段原值，集合子字段走 json.dumps。
        assert body.form_data._fields == [
            ("username", "bob"),
            ("tags", '["admin"]'),
            ("prefs", '{"theme": "light"}'),
        ]


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
        assert response.validated == {
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
        assert response.validated == {
            "filenames": ["file1.txt", "file2.md"],
            "total_size": len("first file") + len("second file content"),
        }


class TestMixedFormAndFile:
    """Form + UploadFile 混合字段 wire-level 测试。

    当存在文件字段时，整体走 multipart：Form 标量字段原值、集合字段 ``json.dumps``
    后写入 FormData。mock_app 暂未提供 Form + File 混合端点，因此保持 wire-level 验证。
    """

    def test_form_and_uploadfile_mix(self, client: Client, tmp_path: pathlib.Path) -> None:
        """Form + UploadFile 共存 → MULTIPART，``FormData`` 同时包含表单字段和文件路径。

        标量子字段原值，集合子字段（list/dict）走 ``json.dumps``。

        :param client: 共享的 Client 实例。
        :param tmp_path: pytest 内置 tmp_path fixture，用于创建临时文件。
        """
        file_path = tmp_path / "avatar.png"
        file_path.write_bytes(b"\x89PNG\r\n\x1a\n")

        endpoint = MixedFormFileRoute(
            data=_LoginForm(
                username="charlie",
                tags=["mix"],
                prefs={"role": "user"},
            ),
            avatar=UploadFile(path=file_path),
        )

        body = client._serialize_body_params(endpoint, endpoint._get_dependant())

        assert body.kind is RequestBodyKind.MULTIPART
        assert isinstance(body.form_data, FormData)
        # BaseModel embed=False 平展：标量子字段原值，集合子字段走 json.dumps。
        assert body.form_data._fields == [
            ("username", "charlie"),
            ("tags", '["mix"]'),
            ("prefs", '{"role": "user"}'),
            ("avatar", file_path),
        ]


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
        assert response.validated == {"filename": None, "size": 0, "content_type": None}

    def test_upload_opt_missing(self, client: Client) -> None:
        """``file: UploadFile | None = None`` + 构造时不传 → 服务端收到 None 占位。

        :param client: 共享的 Client 实例。
        """
        endpoint = UploadOptRoute()  # 缺省值 None
        response = client.send(endpoint)

        assert response.raw.status == 200
        assert response.validated == {"filename": None, "size": 0, "content_type": None}

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
        assert response.validated == {
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
        assert response.validated == {"filenames": [], "total_size": 0}

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
        assert response.validated == {
            "filenames": ["a.txt", "b.md"],
            "total_size": len("first") + len("second"),
        }


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
