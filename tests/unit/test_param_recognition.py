"""T015a: 测试参数自动识别和缓存机制。

验证 APIRoute 能够自动识别参数类型，无需显式标记，并将识别结果缓存：
- 自动识别路径参数（参数名出现在路由 path 中）
- 自动识别查询参数（默认类型）
- 自动识别请求体（BaseModel 子类）
- 显式标记头参数（必须使用 Annotated[Type, Header(...)]）
- 缓存机制正确工作（仅首次识别，后续复用）
"""

from dataclasses import dataclass
from typing import Annotated, Any

from pydantic import BaseModel, Field

from src.dependencies.utils import field_annotation_is_complex
from src.params import Header
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


def test_auto_recognize_path_params() -> None:
    """测试自动识别路径参数（参数名出现在路由 path 中）。"""

    @router.get("/users/{user_id}")
    class GetUser(APIRoute[UserData]):
        user_id: int  # 无需显式标记，在 path 中找到，自动识别为路径参数
        limit: int = 10

    # 获取参数依赖定义
    dependant = GetUser._get_dependant()

    # 验证自动识别结果
    assert len(dependant.path_params) == 1
    assert dependant.path_params[0].name == "user_id"
    assert dependant.path_params[0].alias == "user_id"
    assert len(dependant.query_params) == 1
    assert dependant.query_params[0].name == "limit"
    assert dependant.query_params[0].alias == "limit"

    # 验证参数收集
    endpoint = GetUser(user_id=123, limit=20)
    params = collect_params(endpoint)
    assert params["path"] == {"user_id": 123}
    assert params["query"] == {"limit": 20}


def test_auto_recognize_body_params() -> None:
    """测试自动识别请求体（BaseModel 子类）。"""

    @router.post("/users")
    class CreateUser(APIRoute[UserData]):
        user_data: UserCreateRequest  # 无需显式标记，是 BaseModel，自动识别为请求体
        token: str

    dependant = CreateUser._get_dependant()

    # 验证自动识别结果：BaseModel 子类应该在 pure_body_params 中
    assert len(dependant.pure_body_params) == 1
    assert dependant.pure_body_params[0].name == "user_data"
    assert len(dependant.query_params) == 1
    assert dependant.query_params[0].name == "token"

    # 验证参数收集
    user_req = UserCreateRequest(name="Alice", email="alice@example.com")
    endpoint = CreateUser(user_data=user_req, token="bearer xyz")
    params = collect_params(endpoint)
    assert params["body"] == user_req
    assert params["query"] == {"token": "bearer xyz"}


def test_auto_recognize_query_params() -> None:
    """测试自动识别查询参数（默认类型）。"""

    @router.get("/users")
    class GetUsers(APIRoute[list[UserData]]):
        limit: int = 20
        offset: int = 0
        keyword: str | None = None

    dependant = GetUsers._get_dependant()

    # 所有字段都应该被识别为查询参数（默认）
    assert len(dependant.query_params) == 3
    field_names = [f.name for f in dependant.query_params]
    assert "limit" in field_names
    assert "offset" in field_names
    assert "keyword" in field_names

    # 验证参数收集
    endpoint = GetUsers(limit=50, offset=10, keyword="test")
    params = collect_params(endpoint)
    assert params["query"] == {"limit": 50, "offset": 10, "keyword": "test"}
    assert params["path"] == {}


def test_explicit_header_params() -> None:
    """测试头参数必须显式标记（Annotated[Type, Header(...)]）。"""

    @router.get("/users")
    class GetUsers(APIRoute[list[UserData]]):
        authorization: Annotated[str, Header()] = Field(serialization_alias="Authorization")  # 显式标记为头参数
        x_request_id: Annotated[str, Header()] = Field(serialization_alias="X-Request-ID")  # 显式标记为头参数
        limit: int = 20  # 自动识别为查询参数

    dependant = GetUsers._get_dependant()

    # 验证识别结果
    assert len(dependant.header_params) == 2
    header_names = {f.name: f.alias for f in dependant.header_params}
    assert header_names["authorization"] == "Authorization"
    assert header_names["x_request_id"] == "X-Request-ID"
    assert len(dependant.query_params) == 1
    assert dependant.query_params[0].name == "limit"

    # 验证参数收集
    endpoint = GetUsers(authorization="Bearer token", x_request_id="req-001")
    params = collect_params(endpoint)
    # 头参数应该使用别名作为键
    assert params["header"] == {"Authorization": "Bearer token", "X-Request-ID": "req-001"}
    assert params["query"] == {"limit": 20}


def test_caching_mechanism() -> None:
    """测试缓存机制：装饰器在类定义时自动创建缓存，后续调用复用。"""

    @router.get("/users/{user_id}")
    class GetUser(APIRoute[UserData]):
        user_id: int
        limit: int = 10

    # 装饰器已自动调用 _get_dependant 建立缓存
    assert GetUser._dependant is not None  # 缓存已存在
    dependant1 = GetUser._get_dependant()
    assert len(dependant1.path_params) == 1
    assert dependant1.path_params[0].name == "user_id"
    assert len(dependant1.query_params) == 1
    assert dependant1.query_params[0].name == "limit"

    # 第二次调用 _get_dependant：直接返回缓存
    dependant2 = GetUser._get_dependant()
    assert dependant2 is dependant1  # 返回同一个对象（缓存复用）

    # 多个实例共享同一个缓存
    endpoint1 = GetUser(user_id=1, limit=20)
    endpoint2 = GetUser(user_id=2, limit=30)

    # 两个实例的参数收集都使用同一个缓存
    params1 = collect_params(endpoint1)
    params2 = collect_params(endpoint2)

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
        token: Annotated[str, Header()] = Field(serialization_alias="Authorization")  # 头参数
        data: UserCreateRequest  # 请求体

    dependant = UpdateUserPost._get_dependant()

    # 验证所有参数类型都被正确识别
    assert len(dependant.path_params) == 2
    path_names = [f.name for f in dependant.path_params]
    assert "user_id" in path_names
    assert "post_id" in path_names
    assert len(dependant.query_params) == 1
    assert dependant.query_params[0].name == "published"
    assert len(dependant.header_params) == 1
    assert dependant.header_params[0].name == "token"
    assert len(dependant.pure_body_params) == 1
    assert dependant.pure_body_params[0].name == "data"

    # 验证参数收集
    user_data = UserCreateRequest(name="Bob", email="bob@example.com")
    endpoint = UpdateUserPost(
        user_id=123,
        post_id=456,
        published=True,
        token="Bearer token123",
        data=user_data,
    )
    params = collect_params(endpoint)

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

    dependant = GetTeamMember._get_dependant()

    # 所有在路径中的参数都应被识别
    assert len(dependant.path_params) == 3
    path_names = [f.name for f in dependant.path_params]
    assert "org_id" in path_names
    assert "team_id" in path_names
    assert "member_id" in path_names
    assert len(dependant.query_params) == 1
    assert dependant.query_params[0].name == "include_profile"

    # 验证参数收集
    endpoint = GetTeamMember(org_id=1, team_id=2, member_id=3, include_profile=True)
    params = collect_params(endpoint)

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
    dependant1 = GetUser._get_dependant()
    dependant2 = UpdatePost._get_dependant()

    # 缓存相互独立
    assert dependant1 is not dependant2
    # 验证各自的参数
    assert any(f.name == "user_id" for f in dependant1.path_params)
    assert any(f.name == "post_id" for f in dependant2.path_params)
    assert any(f.name == "content" for f in dependant2.query_params)
    assert any(f.name == "limit" for f in dependant1.query_params)


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

    dependant = PostData._get_dependant()

    # BaseModel 子类应该被识别为请求体
    assert len(dependant.pure_body_params) == 2
    body_names = [f.name for f in dependant.pure_body_params]
    assert "request1" in body_names
    assert "request2" in body_names
    assert len(dependant.query_params) == 1
    assert dependant.query_params[0].name == "query_param"

    # 验证参数收集
    custom_req = CustomRequest(field1="test", field2=42)
    nested_req = NestedRequest(custom=custom_req, extra="data")
    endpoint = PostData(request1=custom_req, request2=nested_req)
    params = collect_params(endpoint)

    # 注意：Body 参数会被后面的覆盖
    assert params["body"] == nested_req  # 最后一个 Body 参数生效
    assert params["query"] == {"query_param": "default"}


def test_sequence_types_recognition() -> None:
    """测试序列类型（list、dict、set）识别为请求体。"""

    @router.post("/items")
    class PostItems(APIRoute[dict[str, str]]):
        items: list[str]  # 序列类型 → body
        metadata: dict[str, int]  # Mapping 类型 → body
        tags: set[str]  # 序列类型 → body
        count: int  # 标量类型 → query

    dependant = PostItems._get_dependant()

    # 序列类型应该在 pure_body_params 中
    assert len(dependant.pure_body_params) == 3
    body_names = [f.name for f in dependant.pure_body_params]
    assert "items" in body_names
    assert "metadata" in body_names
    assert "tags" in body_names
    # 标量类型应该在 query_params 中
    assert len(dependant.query_params) == 1
    assert dependant.query_params[0].name == "count"


def test_dataclass_recognition() -> None:
    """测试 dataclass 识别为请求体。"""
    from dataclasses import dataclass

    @dataclass
    class ItemData:
        name: str
        quantity: int

    @router.post("/dataclass-item")
    class PostDataclass(APIRoute[dict[str, str]]):
        item: ItemData  # dataclass → body
        active: bool  # 标量类型 → query

    dependant = PostDataclass._get_dependant()

    # dataclass 应该在 pure_body_params 中
    assert len(dependant.pure_body_params) == 1
    assert dependant.pure_body_params[0].name == "item"
    # 标量类型应该在 query_params 中
    assert len(dependant.query_params) == 1
    assert dependant.query_params[0].name == "active"


def test_union_type_recognition() -> None:
    """测试 Union 类型识别。

    - BaseModel | None → body（BaseModel 是复杂类型）
    - int | str → query（都不是复杂类型）
    - BaseModel | int → body（任一复杂类型）
    """

    @router.post("/union-item")
    class PostUnion(APIRoute[dict[str, str]]):
        # BaseModel | None → body
        optional_data: UserData | None
        # int | str → query
        optional_id: int | str = "1"
        # 标量
        name: str

    dependant = PostUnion._get_dependant()

    # BaseModel | None 应该在 pure_body_params 中
    assert len(dependant.pure_body_params) == 1
    assert dependant.pure_body_params[0].name == "optional_data"
    # int | str 和 str 应该在 query_params 中
    assert len(dependant.query_params) == 2
    query_names = [f.name for f in dependant.query_params]
    assert "optional_id" in query_names
    assert "name" in query_names


class TestComplexTypeHelpers:
    """测试复杂类型判断辅助函数。"""

    def test_is_complex_base_model(self) -> None:
        """测试 BaseModel 子类被识别为复杂类型。"""
        from src.dependencies.utils import field_annotation_is_complex

        class MyModel(BaseModel):
            field: str

        assert field_annotation_is_complex(MyModel) is True
        assert field_annotation_is_complex(MyModel | None) is True

    def test_is_complex_sequence(self) -> None:
        """测试序列类型被识别为复杂类型。"""
        from src.dependencies.utils import field_annotation_is_complex

        assert field_annotation_is_complex(list[str]) is True
        assert field_annotation_is_complex(dict[str, int]) is True
        assert field_annotation_is_complex(set[int]) is True
        assert field_annotation_is_complex(tuple[int, ...]) is True

    def test_is_complex_dataclass(self) -> None:
        """测试 dataclass 被识别为复杂类型。"""

        @dataclass
        class MyData:
            name: str

        assert field_annotation_is_complex(MyData) is True

    def test_is_complex_scalar(self) -> None:
        """测试标量类型不被识别为复杂类型。"""
        from src.dependencies.utils import field_annotation_is_complex

        assert field_annotation_is_complex(int) is False
        assert field_annotation_is_complex(str) is False
        assert field_annotation_is_complex(bool) is False
        assert field_annotation_is_complex(float) is False
        assert field_annotation_is_complex(int | str) is False  # Union of scalars

    def test_is_complex_union_with_base_model(self) -> None:
        """测试 BaseModel | None 被识别为复杂类型。"""
        from src.dependencies.utils import field_annotation_is_complex

        assert field_annotation_is_complex(UserData | None) is True
        assert field_annotation_is_complex(int | UserData) is True  # One is complex
