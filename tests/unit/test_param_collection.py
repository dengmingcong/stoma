"""T015 + T015a: 测试参数收集和自动识别逻辑。

验证 APIRoute._collect_params() 方法能够正确从实例字段中提取：
- Query 参数（自动识别或显式标记）
- Path 参数（参数名出现在路由 path 中）
- Header 参数（必须显式标记）
- Body 数据（BaseModel 子类自动识别或显式标记）

同时测试参数自动识别机制：
- 无需显式标记的自动参数识别
- 缓存机制确保性能
"""

from typing import Annotated

from pydantic import BaseModel

from src.params import Body, Header, Path, Query
from src.routing import APIRoute, APIRouter

# 创建测试用的路由器
router = APIRouter(servers=["https://api.example.com"])


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


def test_collect_query_params() -> None:
    """测试收集查询参数。"""

    @router.get("/users")
    class GetUsers(APIRoute[list[UserData]]):
        limit: Annotated[int, Query()] = 20
        offset: Annotated[int, Query()] = 0
        keyword: Annotated[str | None, Query()] = None

    # 测试默认值
    endpoint1 = GetUsers()
    params1 = endpoint1._collect_params()
    assert params1["query"] == {"limit": 20, "offset": 0, "keyword": None}
    assert params1["path"] == {}
    assert params1["header"] == {}
    assert params1["body"] is None

    # 测试自定义值
    endpoint2 = GetUsers(limit=50, offset=10, keyword="test")
    params2 = endpoint2._collect_params()
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
    params = endpoint._collect_params()
    assert params["query"] == {}
    assert params["path"] == {"user_id": 123, "post_id": 456}
    assert params["header"] == {}
    assert params["body"] is None


def test_collect_header_params() -> None:
    """测试收集请求头参数。"""

    @router.get("/users")
    class GetUsers(APIRoute[list[UserData]]):
        authorization: Annotated[str, Header(alias="Authorization")]
        x_request_id: Annotated[str, Header(alias="X-Request-ID")]
        accept: Annotated[str, Header()] = "application/json"

    endpoint = GetUsers(
        authorization="Bearer token123",
        x_request_id="req-001",
        accept="application/json",
    )
    params = endpoint._collect_params()
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
    params = endpoint._collect_params()
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
        authorization: Annotated[str, Header(alias="Authorization")]
        body: Annotated[dict[str, str], Body()]

    post_data = {"title": "Hello World", "content": "Test content"}
    endpoint = CreateUserPost(
        user_id=123,
        published=True,
        authorization="Bearer token",
        body=post_data,
    )
    params = endpoint._collect_params()
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
    params = endpoint._collect_params()
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
        page_size: Annotated[int, Query(alias="pageSize")] = 20
        page_num: Annotated[int, Query(alias="pageNum")] = 1

    endpoint = GetUsers(page_size=50, page_num=2)
    params = endpoint._collect_params()
    # 应该使用别名作为键
    assert params["query"] == {"pageSize": 50, "pageNum": 2}
    assert params["path"] == {}
    assert params["header"] == {}
    assert params["body"] is None


def test_multiple_body_params() -> None:
    """测试多个 Body 参数（虽然不常见）。

    在实际场景中通常只有一个 Body，但此测试确保代码能处理多个的情况。
    最后一个 Body 会覆盖前面的。
    """

    @router.post("/data")
    class PostData(APIRoute[dict[str, int]]):
        data1: Annotated[dict[str, int], Body()]
        data2: Annotated[dict[str, int], Body()]

    endpoint = PostData(data1={"a": 1}, data2={"b": 2})
    params = endpoint._collect_params()
    # 最后一个 Body 参数生效
    assert params["body"] == {"b": 2}
