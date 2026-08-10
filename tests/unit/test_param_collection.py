"""T015 + T015a: 测试参数收集和自动识别逻辑。

验证从 APIRoute 实例中能够正确提取参数信息：
- Query 参数（自动识别或显式标记）
- Path 参数（参数名出现在路由 path 中）
- Header 参数（必须显式标记）
- Body 数据（BaseModel 子类自动识别或显式标记）

同时测试参数自动识别机制：
- 无需显式标记的自动参数识别
- 缓存机制确保性能
"""

from typing import Annotated, Any

from pydantic import BaseModel, Field

from src.client import Client
from src.params import Body, Header, Path, Query
from src.routing import APIRoute, APIRouter

# 创建测试用的路由器
router = APIRouter()


# 测试用的响应模型
class UserData(BaseModel):
    """用户数据模型。"""

    id: int
    name: str
    email: str


class UserCreateRequest(BaseModel):
    """创建用户请求模型。"""

    name: str
    email: str
    age: int | None = None


def collect_params(endpoint: APIRoute[Any]) -> dict[str, dict[str, Any] | Any]:
    """辅助函数：从 endpoint 收集参数。

    直接使用 Dependant 来收集参数值。

    :param endpoint: APIRoute 实例。
    :return: 包含 query, path, header, body 的字典。
    """
    dependant = endpoint._get_dependant()

    query_params = {field.alias: getattr(endpoint, field.name) for field in dependant.query_params}
    path_params = {field.alias: getattr(endpoint, field.name) for field in dependant.path_params}
    header_params = {field.alias: getattr(endpoint, field.name) for field in dependant.header_params}

    body_data = None
    if dependant.pure_body_params:
        # 通常只有一个 body，取最后一个
        body_data = getattr(endpoint, dependant.pure_body_params[-1].name)

    return {
        "query": query_params,
        "path": path_params,
        "header": header_params,
        "body": body_data,
    }


def test_collect_query_params() -> None:
    """测试收集查询参数。"""

    @router.get("/users")
    class GetUsers(APIRoute[list[UserData]]):
        limit: Annotated[int, Query()] = 20
        offset: Annotated[int, Query()] = 0
        keyword: Annotated[str | None, Query()] = None

    # 测试默认值
    endpoint1 = GetUsers()
    params1 = collect_params(endpoint1)
    assert params1["query"] == {"limit": 20, "offset": 0, "keyword": None}
    assert params1["path"] == {}
    assert params1["header"] == {}
    assert params1["body"] is None

    # 测试自定义值
    endpoint2 = GetUsers(limit=50, offset=10, keyword="test")
    params2 = collect_params(endpoint2)
    assert params2["query"] == {"limit": 50, "offset": 10, "keyword": "test"}
    assert params2["path"] == {}
    assert params2["header"] == {}
    assert params2["body"] is None


def test_collect_path_params() -> None:
    """测试收集路径参数。"""

    @router.get("/users/{user_id}/posts/{post_id}")
    class GetUserPost(APIRoute[dict[str, str]]):
        user_id: Annotated[int, Path()]
        post_id: Annotated[int, Path()]

    endpoint = GetUserPost(user_id=123, post_id=456)
    params = collect_params(endpoint)
    assert params["query"] == {}
    assert params["path"] == {"user_id": 123, "post_id": 456}
    assert params["header"] == {}
    assert params["body"] is None


def test_collect_header_params() -> None:
    """测试收集请求头参数。"""

    @router.get("/users")
    class GetUsers(APIRoute[list[UserData]]):
        authorization: Annotated[str, Header()] = Field(serialization_alias="Authorization")
        x_request_id: Annotated[str, Header()] = Field(serialization_alias="X-Request-ID")
        accept: Annotated[str, Header()] = "application/json"

    endpoint = GetUsers(
        authorization="Bearer token123",
        x_request_id="req-001",
        accept="application/json",
    )
    params = collect_params(endpoint)
    assert params["query"] == {}
    assert params["path"] == {}
    assert params["header"] == {
        "Authorization": "Bearer token123",
        "X-Request-ID": "req-001",
        "accept": "application/json",
    }
    assert params["body"] is None


def test_collect_body_data() -> None:
    """测试收集请求体数据。"""

    @router.post("/users")
    class CreateUser(APIRoute[UserData]):
        body: Annotated[UserCreateRequest, Body()]

    user_data = UserCreateRequest(name="Alice", email="alice@example.com", age=30)
    endpoint = CreateUser(body=user_data)
    params = collect_params(endpoint)
    assert params["query"] == {}
    assert params["path"] == {}
    assert params["header"] == {}
    assert params["body"] == user_data
    assert isinstance(params["body"], UserCreateRequest)
    assert params["body"].name == "Alice"
    assert params["body"].email == "alice@example.com"


def test_collect_mixed_params() -> None:
    """测试收集混合参数类型。"""

    @router.post("/users/{user_id}/posts")
    class CreateUserPost(APIRoute[dict[str, str]]):
        user_id: Annotated[int, Path()]
        published: Annotated[bool, Query()] = False
        authorization: Annotated[str, Header()] = Field(serialization_alias="Authorization")
        body: Annotated[dict[str, str], Body()]

    post_data = {"title": "Hello World", "content": "Test content"}
    endpoint = CreateUserPost(
        user_id=123,
        published=True,
        authorization="Bearer token",
        body=post_data,
    )
    params = collect_params(endpoint)
    assert params["query"] == {"published": True}
    assert params["path"] == {"user_id": 123}
    assert params["header"] == {"Authorization": "Bearer token"}
    assert params["body"] == post_data


def test_collect_params_with_no_annotations() -> None:
    """测试没有显式参数标记的字段会被自动识别为查询参数（新设计）。

    根据新的自动识别规则，没有显式标记的字段会根据规则自动识别：
    - 如果字段名在路径中 → 路径参数
    - 如果字段类型是 BaseModel 子类 → 请求体
    - 否则 → 查询参数（默认）
    """

    @router.get("/users")
    class GetUsers(APIRoute[list[UserData]]):
        limit: Annotated[int, Query()] = 20
        # 没有显式参数标记的字段，会被自动识别为查询参数
        internal_flag: bool = True

    endpoint = GetUsers(limit=10, internal_flag=False)
    params = collect_params(endpoint)
    # internal_flag 被自动识别为查询参数
    assert params["query"] == {"limit": 10, "internal_flag": False}
    assert params["path"] == {}
    assert params["header"] == {}
    assert params["body"] is None


def test_param_alias() -> None:
    """测试参数别名功能。"""

    @router.get("/users")
    class GetUsers(APIRoute[list[UserData]]):
        # 使用别名
        page_size: Annotated[int, Query()] = Field(serialization_alias="pageSize", default=20)
        page_num: Annotated[int, Query()] = Field(serialization_alias="pageNum", default=1)

    endpoint = GetUsers(page_size=50, page_num=2)
    params = collect_params(endpoint)
    # 应该使用别名作为键
    assert params["query"] == {"pageSize": 50, "pageNum": 2}
    assert params["path"] == {}
    assert params["header"] == {}
    assert params["body"] is None


def test_multiple_body_params() -> None:
    """测试多个 Body 参数（FastAPI 兼容）。

    多个 body 参数序列化时每个独立命名，避免字段冲突。
    """

    @router.post("/data")
    class PostData(APIRoute[dict[str, Any]]):
        data1: Annotated[dict[str, int], Body()]
        data2: Annotated[dict[str, int], Body()]

    endpoint = PostData(data1={"a": 1}, data2={"b": 2})
    body_data = Client(context=None)._serialize_body_params(endpoint, endpoint._get_dependant()).json_body
    assert body_data is not None
    # 多个 body 参数 → 每个独立命名
    assert body_data == {"data1": {"a": 1}, "data2": {"b": 2}}


def test_single_pydantic_body_flat() -> None:
    """测试单个 Pydantic 模型 body（自动识别）平展。

    单 body Pydantic 模型默认 embed=False，模型字段作为顶层 key。
    """

    @router.post("/users")
    class CreateUser(APIRoute[dict[str, Any]]):
        data: UserCreateRequest

    endpoint = CreateUser(data=UserCreateRequest(name="Alice", email="alice@example.com", age=30))
    body_data = Client(context=None)._serialize_body_params(endpoint, endpoint._get_dependant()).json_body
    assert body_data is not None
    # 单 Pydantic 模型自动识别 → 平展
    assert body_data == {"name": "Alice", "email": "alice@example.com", "age": 30}


def test_single_pydantic_body_embed_true() -> None:
    """测试 Body(embed=True) 显式嵌入。"""

    @router.post("/users-embed")
    class CreateUserEmbed(APIRoute[dict[str, Any]]):
        data: Annotated[UserCreateRequest, Body(embed=True)]

    endpoint = CreateUserEmbed(data=UserCreateRequest(name="Bob", email="bob@example.com"))
    body_data = Client(context=None)._serialize_body_params(endpoint, endpoint._get_dependant()).json_body
    assert body_data is not None
    # Body(embed=True) → 嵌入到 data 键下
    assert body_data == {"data": {"name": "Bob", "email": "bob@example.com"}}


def test_single_scalar_body_embedded() -> None:
    """测试标量 Body() 默认嵌入（标量必须嵌入）。"""

    @router.post("/importance")
    class SetImportance(APIRoute[dict[str, Any]]):
        importance: Annotated[int, Body()]

    endpoint = SetImportance(importance=5)
    body_data = Client(context=None)._serialize_body_params(endpoint, endpoint._get_dependant()).json_body
    assert body_data is not None
    # 标量必须嵌入（无法平展）
    assert body_data == {"importance": 5}


def test_multiple_body_pydantic_and_scalar() -> None:
    """测试多个 body 参数：Pydantic 模型 + 标量，每个独立命名。"""

    @router.post("/multi")
    class CreateItem(APIRoute[dict[str, Any]]):
        item: UserCreateRequest
        importance: Annotated[int, Body()]

    endpoint = CreateItem(
        item=UserCreateRequest(name="Charlie", email="charlie@example.com"),
        importance=10,
    )
    body_data = Client(context=None)._serialize_body_params(endpoint, endpoint._get_dependant()).json_body
    assert body_data is not None
    # 多个 body → 每个独立命名
    assert body_data == {
        "item": {"name": "Charlie", "email": "charlie@example.com"},
        "importance": 10,
    }


def test_api_route_without_generic() -> None:
    """测试 APIRoute 不带泛型参数的情况。"""

    router2 = APIRouter()

    @router2.get("/health")
    class HealthCheck(APIRoute):
        status: str = "ok"

    dependant = HealthCheck._get_dependant()
    # json_response_schema 为 None，不校验响应
    assert dependant.json_response_schema is None
    assert dependant.json_response_schema_adapter is None
    # 但参数收集正常
    assert len(dependant.query_params) == 1
    assert dependant.query_params[0].name == "status"
