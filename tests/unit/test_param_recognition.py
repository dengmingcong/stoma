"""T015a: 测试参数自动识别和缓存机制。

验证 APIRoute 能够自动识别参数类型，无需显式标记，并将识别结果缓存：
- 自动识别路径参数（参数名出现在路由 path 中）
- 自动识别查询参数（默认类型）
- 自动识别请求体（BaseModel 子类）
- 显式标记头参数（必须使用 Annotated[Type, Header(...)]）
- 缓存机制正确工作（仅首次识别，后续复用）
"""

from typing import Annotated

from pydantic import BaseModel

from src.params import Header, ParamTypes
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


def test_auto_recognize_path_params() -> None:
    """测试自动识别路径参数（参数名出现在路由 path 中）。"""

    @router.get("/users/{user_id}")
    class GetUser(APIRoute[UserData]):
        user_id: int  # 无需显式标记，在 path 中找到，自动识别为路径参数
        limit: int = 10

    # 获取参数映射
    mapping = GetUser._get_param_mapping()

    # 验证自动识别结果
    assert mapping["user_id"] == ParamTypes.path
    assert mapping["limit"] == ParamTypes.query

    # 验证参数收集
    endpoint = GetUser(user_id=123, limit=20)
    params = endpoint._collect_params()
    assert params["path"] == {"user_id": 123}
    assert params["query"] == {"limit": 20}


def test_auto_recognize_body_params() -> None:
    """测试自动识别请求体（BaseModel 子类）。"""

    @router.post("/users")
    class CreateUser(APIRoute[UserData]):
        user_data: UserCreateRequest  # 无需显式标记，是 BaseModel，自动识别为请求体
        token: str

    mapping = CreateUser._get_param_mapping()

    # 验证自动识别结果
    assert mapping["user_data"] == ParamTypes.body
    assert mapping["token"] == ParamTypes.query

    # 验证参数收集
    user_req = UserCreateRequest(name="Alice", email="alice@example.com")
    endpoint = CreateUser(user_data=user_req, token="bearer xyz")
    params = endpoint._collect_params()
    assert params["body"] == user_req
    assert params["query"] == {"token": "bearer xyz"}


def test_auto_recognize_query_params() -> None:
    """测试自动识别查询参数（默认类型）。"""

    @router.get("/users")
    class GetUsers(APIRoute[list[UserData]]):
        limit: int = 20
        offset: int = 0
        keyword: str | None = None

    mapping = GetUsers._get_param_mapping()

    # 所有字段都应该被识别为查询参数（默认）
    assert mapping["limit"] == ParamTypes.query
    assert mapping["offset"] == ParamTypes.query
    assert mapping["keyword"] == ParamTypes.query

    # 验证参数收集
    endpoint = GetUsers(limit=50, offset=10, keyword="test")
    params = endpoint._collect_params()
    assert params["query"] == {"limit": 50, "offset": 10, "keyword": "test"}
    assert params["path"] == {}


def test_explicit_header_params() -> None:
    """测试头参数必须显式标记（Annotated[Type, Header(...)]）。"""

    @router.get("/users")
    class GetUsers(APIRoute[list[UserData]]):
        authorization: Annotated[str, Header(alias="Authorization")]  # 显式标记为头参数
        x_request_id: Annotated[str, Header(alias="X-Request-ID")]  # 显式标记为头参数
        limit: int = 20  # 自动识别为查询参数

    mapping = GetUsers._get_param_mapping()

    # 验证识别结果
    assert mapping["authorization"] == ParamTypes.header
    assert mapping["x_request_id"] == ParamTypes.header
    assert mapping["limit"] == ParamTypes.query

    # 验证参数收集
    endpoint = GetUsers(authorization="Bearer token", x_request_id="req-001")
    params = endpoint._collect_params()
    # 头参数应该使用别名作为键
    assert params["header"] == {"Authorization": "Bearer token", "X-Request-ID": "req-001"}
    assert params["query"] == {"limit": 20}


def test_caching_mechanism() -> None:
    """测试缓存机制：参数识别仅执行一次，后续复用缓存。"""

    @router.get("/users/{user_id}")
    class GetUser(APIRoute[UserData]):
        user_id: int
        limit: int = 10

    # 首次调用 _get_param_mapping：构建映射
    assert GetUser._param_mapping is None  # 初始状态为 None
    mapping1 = GetUser._get_param_mapping()
    assert GetUser._param_mapping is not None  # 缓存已建立
    assert mapping1["user_id"] == ParamTypes.path
    assert mapping1["limit"] == ParamTypes.query

    # 第二次调用 _get_param_mapping：直接返回缓存
    mapping2 = GetUser._get_param_mapping()
    assert mapping2 is mapping1  # 返回同一个对象（缓存复用）

    # 多个实例共享同一个缓存
    endpoint1 = GetUser(user_id=1, limit=20)
    endpoint2 = GetUser(user_id=2, limit=30)

    # 两个实例的参数收集都使用同一个缓存
    params1 = endpoint1._collect_params()
    params2 = endpoint2._collect_params()

    assert params1["path"] == {"user_id": 1}
    assert params2["path"] == {"user_id": 2}
    assert params1["query"] == {"limit": 20}
    assert params2["query"] == {"limit": 30}


def test_complex_mixed_params() -> None:
    """测试复杂场景：混合所有参数类型。"""

    @router.post("/users/{user_id}/posts/{post_id}")
    class UpdateUserPost(APIRoute[dict[str, str]]):
        user_id: int  # 路径参数
        post_id: int  # 路径参数
        published: bool = False  # 查询参数
        token: Annotated[str, Header(alias="Authorization")]  # 头参数
        data: UserCreateRequest  # 请求体

    mapping = UpdateUserPost._get_param_mapping()

    # 验证所有参数类型都被正确识别
    assert mapping["user_id"] == ParamTypes.path
    assert mapping["post_id"] == ParamTypes.path
    assert mapping["published"] == ParamTypes.query
    assert mapping["token"] == ParamTypes.header
    assert mapping["data"] == ParamTypes.body

    # 验证参数收集
    user_data = UserCreateRequest(name="Bob", email="bob@example.com")
    endpoint = UpdateUserPost(
        user_id=123,
        post_id=456,
        published=True,
        token="Bearer token123",
        data=user_data,
    )
    params = endpoint._collect_params()

    assert params["path"] == {"user_id": 123, "post_id": 456}
    assert params["query"] == {"published": True}
    assert params["header"] == {"Authorization": "Bearer token123"}
    assert params["body"] == user_data


def test_path_param_extraction() -> None:
    """测试路径参数的正确提取（支持多个路径参数）。"""

    @router.get("/orgs/{org_id}/teams/{team_id}/members/{member_id}")
    class GetTeamMember(APIRoute[UserData]):
        org_id: int
        team_id: int
        member_id: int
        include_profile: bool = False

    mapping = GetTeamMember._get_param_mapping()

    # 所有在路径中的参数都应被识别
    assert mapping["org_id"] == ParamTypes.path
    assert mapping["team_id"] == ParamTypes.path
    assert mapping["member_id"] == ParamTypes.path
    assert mapping["include_profile"] == ParamTypes.query

    # 验证参数收集
    endpoint = GetTeamMember(org_id=1, team_id=2, member_id=3, include_profile=True)
    params = endpoint._collect_params()

    assert params["path"] == {"org_id": 1, "team_id": 2, "member_id": 3}
    assert params["query"] == {"include_profile": True}


def test_param_recognition_across_routes() -> None:
    """测试不同路由的参数识别相互独立。"""

    @router.get("/users/{user_id}")
    class GetUser(APIRoute[UserData]):
        user_id: int
        limit: int = 10

    @router.post("/posts/{post_id}")
    class UpdatePost(APIRoute[dict[str, str]]):
        post_id: int
        content: str

    # 两个不同的路由应该各自维护自己的缓存
    mapping1 = GetUser._get_param_mapping()
    mapping2 = UpdatePost._get_param_mapping()

    # 缓存相互独立
    assert mapping1 is not mapping2
    assert "user_id" in mapping1
    assert "post_id" in mapping2
    assert "content" in mapping2
    assert "limit" in mapping1


def test_basemodel_subclass_recognition() -> None:
    """测试 BaseModel 子类的正确识别为请求体。"""

    class CustomRequest(BaseModel):
        """自定义请求模型。"""

        field1: str
        field2: int

    class NestedRequest(BaseModel):
        """嵌套请求模型。"""

        custom: CustomRequest
        extra: str

    @router.post("/data")
    class PostData(APIRoute[dict[str, str]]):
        request1: CustomRequest  # BaseModel 子类
        request2: NestedRequest  # BaseModel 子类
        query_param: str = "default"  # 不是 BaseModel

    mapping = PostData._get_param_mapping()

    # BaseModel 子类应该被识别为请求体
    assert mapping["request1"] == ParamTypes.body
    assert mapping["request2"] == ParamTypes.body
    assert mapping["query_param"] == ParamTypes.query

    # 验证参数收集
    custom_req = CustomRequest(field1="test", field2=42)
    nested_req = NestedRequest(custom=custom_req, extra="data")
    endpoint = PostData(request1=custom_req, request2=nested_req)
    params = endpoint._collect_params()

    # 注意：Body 参数会被后面的覆盖
    assert params["body"] == nested_req  # 最后一个 Body 参数生效
    assert params["query"] == {"query_param": "default"}
