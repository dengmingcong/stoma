"""``src.routing`` 的 ``APIRouter`` / ``APIRoute`` 分类与依赖识别单元测试。

合并自以下历史文件：

- :mod:`tests.unit.test_param_collection` —— 参数收集 / 别名 / Body 平展 / Body 多参数
  / 不带泛型的 APIRoute / ``Body`` 与 ``Form/UploadFile`` 互斥 / ``upload_as_multipart=False``
  启动期校验。
- :mod:`tests.unit.test_param_recognition` —— 自动识别路径 / query / header / body、
  缓存机制、跨路由独立、BaseModel / 序列 / dataclass / Union 识别。
- :mod:`tests.unit.test_routing_classification` —— Form-marked 文件类型 → raise；
  Form-marked 标量 → ``form_body_params``；混用场景。

``field_annotation_is_complex`` 与 ``validate_binary_body_annotation`` 单元覆盖在
:mod:`tests.unit.dependencies.test_annotation`，``APIRoute._serialize_body_params``
对 Form / UploadFile / RawPayload 的实现细节在 :mod:`tests.unit.dependencies.test_request`。
"""

import pathlib
from dataclasses import dataclass
from typing import Annotated, Any, ClassVar

import pytest
from pydantic import BaseModel, Field

from stoma import Body, Form, Header, Path, Query, UploadFile
from stoma.dependencies.request import RequestBodyKind, _serialize_body_params
from stoma.routing import APIRoute, APIRouter

router = APIRouter()


# ===== 测试响应模型 =====


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


# ===== 收集参数辅助函数 =====


def collect_params(endpoint: APIRoute[Any]) -> dict[str, dict[str, Any] | Any]:
    """辅助函数：从 endpoint 收集 query / path / header / body 参数。

    :param endpoint: APIRoute 实例。
    :return: 包含 ``query``、``path``、``header``、``body`` 的字典。
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


# ===== 参数收集（显式 Query/Path/Header/Body 注解）=====


def test_collect_query_params() -> None:
    """测试收集查询参数。"""

    @router.get("/users")
    class GetUsers(APIRoute[list[UserData]]):
        limit: Annotated[int, Query()] = 20
        offset: Annotated[int, Query()] = 0
        keyword: Annotated[str | None, Query()] = None

    # 默认值
    endpoint1 = GetUsers()
    params1 = collect_params(endpoint1)
    assert params1["query"] == {"limit": 20, "offset": 0, "keyword": None}
    assert params1["path"] == {}
    assert params1["header"] == {}
    assert params1["body"] is None

    # 自定义值
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
    """测试没有显式参数标记的字段会被自动识别为查询参数。

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
    # ``internal_flag`` 被自动识别为查询参数
    assert params["query"] == {"limit": 10, "internal_flag": False}
    assert params["path"] == {}
    assert params["header"] == {}
    assert params["body"] is None


def test_param_alias() -> None:
    """测试参数别名功能。"""

    @router.get("/users")
    class GetUsers(APIRoute[list[UserData]]):
        page_size: Annotated[int, Query()] = Field(serialization_alias="pageSize", default=20)
        page_num: Annotated[int, Query(), Field(serialization_alias="pageNum", default=1)]

    endpoint = GetUsers(page_size=50, page_num=2)
    params = collect_params(endpoint)
    # 应该使用别名作为键
    assert params["query"] == {"pageSize": 50, "pageNum": 2}
    assert params["path"] == {}
    assert params["header"] == {}
    assert params["body"] is None


# ===== Body 平展与多参数 =====


def test_multiple_body_params() -> None:
    """测试多个 Body 参数（FastAPI 兼容）。"""

    @router.post("/data")
    class PostData(APIRoute[dict[str, Any]]):
        data1: Annotated[dict[str, int], Body()]
        data2: Annotated[dict[str, int], Body()]

    endpoint = PostData(data1={"a": 1}, data2={"b": 2})
    body_data = _serialize_body_params(endpoint, endpoint._get_dependant()).raw_data.value
    assert body_data is not None
    # 多个 body 参数 → 每个独立命名
    assert body_data == {"data1": {"a": 1}, "data2": {"b": 2}}


def test_single_pydantic_body_flat() -> None:
    """测试单个 Pydantic 模型 body（自动识别）平展。"""

    @router.post("/users")
    class CreateUser(APIRoute[dict[str, Any]]):
        data: UserCreateRequest

    endpoint = CreateUser(data=UserCreateRequest(name="Alice", email="alice@example.com", age=30))
    body_data = _serialize_body_params(endpoint, endpoint._get_dependant()).raw_data.value
    assert body_data is not None
    # 单 Pydantic 模型自动识别 → 平展
    assert body_data == {"name": "Alice", "email": "alice@example.com", "age": 30}


def test_single_pydantic_body_embed_true() -> None:
    """测试 ``Body(embed=True)`` 显式嵌入。"""

    @router.post("/users-embed")
    class CreateUserEmbed(APIRoute[dict[str, Any]]):
        data: Annotated[UserCreateRequest, Body(embed=True)]

    endpoint = CreateUserEmbed(data=UserCreateRequest(name="Bob", email="bob@example.com"))
    body_data = _serialize_body_params(endpoint, endpoint._get_dependant()).raw_data.value
    assert body_data is not None
    # ``Body(embed=True)`` → 嵌入到 ``data`` 键下
    assert body_data == {"data": {"name": "Bob", "email": "bob@example.com"}}


def test_single_scalar_body_embedded() -> None:
    """测试标量 ``Body(embed=True)`` 嵌入。"""

    @router.post("/importance")
    class SetImportance(APIRoute[dict[str, Any]]):
        importance: Annotated[int, Body(embed=True)]

    endpoint = SetImportance(importance=5)
    body_data = _serialize_body_params(endpoint, endpoint._get_dependant()).raw_data.value
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
    body_data = _serialize_body_params(endpoint, endpoint._get_dependant()).raw_data.value
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
    # ``json_response_schema`` 为 None，不校验响应
    assert dependant.json_response_schema is None
    assert dependant.json_response_schema_adapter is None
    # 但参数收集正常
    assert len(dependant.query_params) == 1
    assert dependant.query_params[0].name == "status"


def test_pure_form_mutual_exclusion_raise() -> None:
    """测试 ``Body()`` 与 ``Form()`` 不能在同一 APIRoute 混用。"""
    with pytest.raises(ValueError, match="Body 与 Form/UploadFile 字段不能在同一 APIRoute 混用"):

        @router.post("/mixed")
        class MixedRoute(APIRoute[dict[str, Any]]):
            body: Annotated[dict[str, int], Body()]
            note: Annotated[str, Form()]


# ===== 自动识别 / 缓存 / 跨路由 =====


def test_auto_recognize_path_params() -> None:
    """测试自动识别路径参数（参数名出现在路由 path 中）。"""

    @router.get("/users/{user_id}")
    class GetUser(APIRoute[UserData]):
        user_id: int  # 无需显式标记，在 path 中找到，自动识别为路径参数
        limit: int = 10

    dependant = GetUser._get_dependant()

    assert len(dependant.path_params) == 1
    assert dependant.path_params[0].name == "user_id"
    assert dependant.path_params[0].alias == "user_id"
    assert len(dependant.query_params) == 1
    assert dependant.query_params[0].name == "limit"
    assert dependant.query_params[0].alias == "limit"

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

    # BaseModel 子类应该在 ``pure_body_params`` 中
    assert len(dependant.pure_body_params) == 1
    assert dependant.pure_body_params[0].name == "user_data"
    assert len(dependant.query_params) == 1
    assert dependant.query_params[0].name == "token"

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

    endpoint = GetUsers(limit=50, offset=10, keyword="test")
    params = collect_params(endpoint)
    assert params["query"] == {"limit": 50, "offset": 10, "keyword": "test"}
    assert params["path"] == {}


def test_explicit_header_params() -> None:
    """测试头参数必须显式标记（``Annotated[Type, Header(...)]``）。"""

    @router.get("/users")
    class GetUsers(APIRoute[list[UserData]]):
        authorization: Annotated[str, Header()] = Field(serialization_alias="Authorization")
        x_request_id: Annotated[str, Header()] = Field(serialization_alias="X-Request-ID")
        limit: int = 20

    dependant = GetUsers._get_dependant()

    assert len(dependant.header_params) == 2
    header_names = {f.name: f.alias for f in dependant.header_params}
    assert header_names["authorization"] == "Authorization"
    assert header_names["x_request_id"] == "X-Request-ID"
    assert len(dependant.query_params) == 1
    assert dependant.query_params[0].name == "limit"

    endpoint = GetUsers(authorization="Bearer token", x_request_id="req-001")
    params = collect_params(endpoint)
    assert params["header"] == {"Authorization": "Bearer token", "X-Request-ID": "req-001"}
    assert params["query"] == {"limit": 20}


def test_caching_mechanism() -> None:
    """测试缓存机制：装饰器在类定义时自动创建缓存，后续调用复用。"""

    @router.get("/users/{user_id}")
    class GetUser(APIRoute[UserData]):
        user_id: int
        limit: int = 10

    # 装饰器已自动调用 ``_get_dependant`` 建立缓存
    assert GetUser._dependant is not None
    dependant1 = GetUser._get_dependant()
    assert len(dependant1.path_params) == 1
    assert dependant1.path_params[0].name == "user_id"
    assert len(dependant1.query_params) == 1
    assert dependant1.query_params[0].name == "limit"

    # 第二次调用：直接返回缓存
    dependant2 = GetUser._get_dependant()
    assert dependant2 is dependant1

    # 多个实例共享同一个缓存
    endpoint1 = GetUser(user_id=1, limit=20)
    endpoint2 = GetUser(user_id=2, limit=30)
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
        user_id: int
        post_id: int
        published: bool = False
        token: Annotated[str, Header()] = Field(serialization_alias="Authorization")
        data: UserCreateRequest

    dependant = UpdateUserPost._get_dependant()

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

    assert len(dependant.path_params) == 3
    path_names = [f.name for f in dependant.path_params]
    assert "org_id" in path_names
    assert "team_id" in path_names
    assert "member_id" in path_names
    assert len(dependant.query_params) == 1
    assert dependant.query_params[0].name == "include_profile"

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

    dependant1 = GetUser._get_dependant()
    dependant2 = UpdatePost._get_dependant()

    # 缓存相互独立
    assert dependant1 is not dependant2
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

    custom_req = CustomRequest(field1="test", field2=42)
    nested_req = NestedRequest(custom=custom_req, extra="data")
    endpoint = PostData(request1=custom_req, request2=nested_req)
    params = collect_params(endpoint)

    # Body 参数会被后面的覆盖
    assert params["body"] == nested_req
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

    # 序列类型应该在 ``pure_body_params`` 中
    assert len(dependant.pure_body_params) == 3
    body_names = [f.name for f in dependant.pure_body_params]
    assert "items" in body_names
    assert "metadata" in body_names
    assert "tags" in body_names
    # 标量类型应该在 ``query_params`` 中
    assert len(dependant.query_params) == 1
    assert dependant.query_params[0].name == "count"


def test_dataclass_recognition() -> None:
    """测试 dataclass 识别为请求体。"""

    @dataclass
    class ItemData:
        name: str
        quantity: int

    @router.post("/dataclass-item")
    class PostDataclass(APIRoute[dict[str, str]]):
        item: ItemData  # dataclass → body
        active: bool  # 标量类型 → query

    dependant = PostDataclass._get_dependant()

    assert dependant.pure_body_params[0].name == "item"
    assert dependant.query_params[0].name == "active"


def test_union_type_recognition() -> None:
    """测试 Union 类型识别。

    - ``BaseModel | None`` → body（BaseModel 是复杂类型）
    - ``int | str`` → query（都不是复杂类型）
    - ``BaseModel | int`` → body（任一复杂类型）
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

    # BaseModel | None 应该在 ``pure_body_params`` 中
    assert len(dependant.pure_body_params) == 1
    assert dependant.pure_body_params[0].name == "optional_data"
    # int | str 和 str 应该在 ``query_params`` 中
    assert len(dependant.query_params) == 2
    query_names = [f.name for f in dependant.query_params]
    assert "optional_id" in query_names
    assert "name" in query_names


# ===== Form-marked 文件类型路由分类 =====


def get_param_categories(endpoint_cls: type[APIRoute[Any]]) -> dict[str, list[str]]:
    """获取端点的参数分类结果。

    :param endpoint_cls: APIRoute 子类。
    :return: 包含各分类参数名的字典。
    """
    dependant = endpoint_cls._get_dependant()
    return {
        "file_body_params": [f.name for f in dependant.file_body_params],
        "form_body_params": [f.name for f in dependant.form_body_params],
        "pure_body_params": [f.name for f in dependant.pure_body_params],
        "query_params": [f.name for f in dependant.query_params],
    }


def test_form_marked_uploadfile_raises() -> None:
    """``Annotated[UploadFile, Form()]`` → ``ValueError``。"""

    class UploadFileEndpoint(APIRoute[UserData]):
        file: Annotated[UploadFile, Form()]

    with pytest.raises(ValueError, match="Form 不支持的字段类型"):
        UploadFileEndpoint._get_dependant(method="POST", path="/upload")


def test_form_marked_list_uploadfile_raises() -> None:
    """``Annotated[list[UploadFile], Form()]`` → ``ValueError``。"""

    class UploadFilesEndpoint(APIRoute[UserData]):
        files: Annotated[list[UploadFile], Form()]

    with pytest.raises(ValueError, match="Form 不支持的字段类型"):
        UploadFilesEndpoint._get_dependant(method="POST", path="/upload")


def test_form_marked_path_raises() -> None:
    """``Annotated[pathlib.Path, Form()]`` → ``ValueError``。"""

    class UploadPathEndpoint(APIRoute[UserData]):
        file_path: Annotated[pathlib.Path, Form()]

    with pytest.raises(ValueError, match="Form 不支持的字段类型"):
        UploadPathEndpoint._get_dependant(method="POST", path="/upload")


def test_form_marked_str_routes_to_form_body_params() -> None:
    """``Annotated[str, Form()]`` → ``form_body_params``。"""

    @router.post("/submit")
    class SubmitStrEndpoint(APIRoute[UserData]):
        name: Annotated[str, Form()]

    categories = get_param_categories(SubmitStrEndpoint)
    assert "name" in categories["form_body_params"]
    assert "name" not in categories["file_body_params"]


def test_form_marked_list_str_routes_to_form_body_params() -> None:
    """``Annotated[list[str], Form()]`` → ``form_body_params``。"""

    @router.post("/submit")
    class SubmitStrListEndpoint(APIRoute[UserData]):
        tags: Annotated[list[str], Form()]

    categories = get_param_categories(SubmitStrListEndpoint)
    assert "tags" in categories["form_body_params"]
    assert "tags" not in categories["file_body_params"]


def test_form_scalar_optional() -> None:
    """``Annotated[Optional[str], Form()]`` → ``form_body_params``。"""

    @router.post("/submit")
    class SubmitOptionalStrEndpoint(APIRoute[UserData]):
        name: Annotated[str | None, Form()]

    categories = get_param_categories(SubmitOptionalStrEndpoint)
    assert "name" in categories["form_body_params"]
    assert "name" not in categories["file_body_params"]


def test_form_scalar_list_optional() -> None:
    """``Annotated[Optional[list[str]], Form()]`` → ``form_body_params``。"""

    @router.post("/submit")
    class SubmitOptionalStrListEndpoint(APIRoute[UserData]):
        tags: Annotated[list[str] | None, Form()]

    categories = get_param_categories(SubmitOptionalStrListEndpoint)
    assert "tags" in categories["form_body_params"]
    assert "tags" not in categories["file_body_params"]


def test_unmarked_uploadfile_routes_to_file_body_params() -> None:
    """``UploadFile``（无 ``Form`` 标记）→ ``file_body_params``。"""

    @router.post("/upload")
    class UnmarkedUploadEndpoint(APIRoute[UserData]):
        file: UploadFile

    categories = get_param_categories(UnmarkedUploadEndpoint)
    assert "file" in categories["file_body_params"]
    assert "file" not in categories["form_body_params"]


def test_mixed_form_marked_params() -> None:
    """混用 Form-marked 文件类型和普通类型。"""

    @router.post("/mixed")
    class MixedEndpoint(APIRoute[UserData]):
        file: UploadFile
        name: Annotated[str, Form()]

    categories = get_param_categories(MixedEndpoint)
    assert categories["file_body_params"] == ["file"]
    assert categories["form_body_params"] == ["name"]


def test_form_basemodel_raises_in_routing() -> None:
    """``Annotated[BaseModel, Form()]`` → ``ValueError``（Form 不支持该字段类型）。

    不使用 ``@router.post`` 装饰器（其内部 ``update_api_route`` 会调用
    ``_get_dependant()``，导致 raise 在装饰期触发），
    改为直接调用 ``_get_dependant()`` 确保 raise 发生在调用期。
    """

    class SubmitFormEndpoint(APIRoute[UserData]):
        """含 BaseModel Form 字段的路由类。"""

        data: Annotated[UserCreateRequest, Form()]

    with pytest.raises(ValueError, match="Form 不支持的字段类型"):
        SubmitFormEndpoint._get_dependant(method="POST", path="/submit")


def test_form_bytes_annotation_raises_in_routing() -> None:
    """``Annotated[bytes, Form()]`` 在路由分类阶段抛 ``ValueError``。

    Playwright ``FormDataValue`` 不含 ``bytes``，错误消息提示用户
    ``json.dumps`` 为 ``str`` 后传入或改用 ``UploadFile``。
    """

    class BytesFormEndpoint(APIRoute[UserData]):
        """含 bytes Form 字段的路由类。"""

        payload: Annotated[bytes, Form()]

    with pytest.raises(ValueError, match=r"Form 不支持的字段类型.*json\.dumps"):
        BytesFormEndpoint._get_dependant(method="POST", path="/form-bytes")


def test_form_list_bytes_annotation_raises_in_routing() -> None:
    """``Annotated[list[bytes], Form()]`` 在路由分类阶段抛 ``ValueError``。"""

    class BytesListFormEndpoint(APIRoute[UserData]):
        """含 ``list[bytes]`` Form 字段的路由类。"""

        payloads: Annotated[list[bytes], Form()]

    with pytest.raises(ValueError, match=r"Form 不支持的字段类型.*json\.dumps"):
        BytesListFormEndpoint._get_dependant(method="POST", path="/form-bytes-list")


# ===== Form 标记本身的不变量 =====


def test_form_embed_kwarg_removed_raises_type_error() -> None:
    """测试 ``Form`` 不再接受 ``embed`` 关键字参数。"""
    with pytest.raises(TypeError, match="embed"):
        Form(embed=True)


def test_form_no_longer_inherits_body() -> None:
    """``Form.__mro__`` 不含 ``Body``。"""
    from stoma import Body as BodyCls
    from stoma.params import Form

    assert BodyCls not in Form.__mro__


def test_form_has_no_init_method() -> None:
    """``Form.__init__`` 是 ``object.__init__`` / ``Param.__init__``（无自己定义）。"""
    from stoma.params import Form, Param

    assert Form.__init__ is Param.__init__
    assert Form.__init__ is object.__init__


# ===== upload_as_multipart=False 启动期校验 =====


class TestUploadAsMultipartFlag:
    """``upload_as_multipart=False`` 启动期校验。"""

    def test_upload_as_multipart_false_zero_files_raises(self) -> None:
        """无 UploadFile 字段 + flag False → raise。"""

        class R(APIRoute[dict]):
            pass

        with pytest.raises(ValueError, match="upload_as_multipart=False 要求 body 恰好包含一个 UploadFile 字段"):
            R._get_dependant(method="POST", path="/x", upload_as_multipart=False)

    def test_upload_as_multipart_false_two_files_raises(self) -> None:
        """2 个 UploadFile + flag False → raise。"""

        class R(APIRoute[dict]):
            file1: UploadFile
            file2: UploadFile

        with pytest.raises(ValueError, match="实际有 2 个"):
            R._get_dependant(method="POST", path="/x", upload_as_multipart=False)

    def test_upload_as_multipart_false_list_uploadfile_raises(self) -> None:
        """``list[UploadFile]`` + flag False → raise（list 包装不允许）。"""

        class R(APIRoute[dict]):
            files: list[UploadFile]

        with pytest.raises(ValueError, match="不能是 list/Form 包装"):
            R._get_dependant(method="POST", path="/x", upload_as_multipart=False)

    def test_upload_as_multipart_false_with_form_raises(self) -> None:
        """1 UploadFile + 1 Form + flag False → raise。"""

        class R(APIRoute[dict]):
            file: UploadFile
            data: Annotated[str, Form()]

        with pytest.raises(ValueError, match="不允许 Form 字段"):
            R._get_dependant(method="POST", path="/x", upload_as_multipart=False)

    def test_upload_as_multipart_false_with_body_raises(self) -> None:
        """1 UploadFile + 1 Body + flag False → raise。

        注意：现有 "Body 与 Form/UploadFile 混用" 互斥校验会先 fire，
        所以错误消息可能是 "Body 与 Form/UploadFile..." 而非 "不允许 Body() 字段"。
        两种消息都接受。
        """

        class R(APIRoute[dict]):
            file: UploadFile
            data: Annotated[dict, Body()]

        with pytest.raises(
            ValueError,
            match="不允许 Body\\(\\) 字段|Body 与 Form/UploadFile 字段不能在同一 APIRoute 混用",
        ):
            R._get_dependant(method="POST", path="/x", upload_as_multipart=False)

    def test_upload_as_multipart_false_optional_uploadfile_works(self) -> None:
        """``UploadFile | None = None`` + flag False → 通过校验 + Dependant 正确。

        Plan 增强：raw-body 模式现在接受 ``UploadFile | None``（裸 Optional）。
        """
        from types import UnionType
        from typing import get_args, get_origin

        class R(APIRoute[dict]):
            file: UploadFile | None = None

        d = R._get_dependant(method="POST", path="/x", upload_as_multipart=False)
        assert d.upload_as_multipart is False
        assert len(d.file_body_params) == 1
        assert d.file_body_params[0].name == "file"
        ann = d.file_body_params[0].field_info.annotation
        assert get_origin(ann) is UnionType
        assert get_args(ann) == (UploadFile, type(None))

    def test_upload_as_multipart_false_happy_path(self) -> None:
        """1 裸 ``UploadFile`` + flag False → 通过校验 + Dependant 正确。"""

        class R(APIRoute[dict]):
            file: UploadFile

        d = R._get_dependant(method="POST", path="/x", upload_as_multipart=False)
        assert d.upload_as_multipart is False
        assert len(d.file_body_params) == 1
        assert d.file_body_params[0].name == "file"

    def test_upload_as_multipart_default_true_passes(self) -> None:
        """默认值（不传 ``upload_as_multipart=True``）允许裸 ``UploadFile``。"""

        class R(APIRoute[dict]):
            file: UploadFile

        d = R._get_dependant(method="POST", path="/x")
        assert d.upload_as_multipart is True
        assert len(d.file_body_params) == 1


# ===== Body 多参数 embed 行为 =====


def test_body_embed_ignored_with_multiple_params() -> None:
    """多 body 参数时 ``Body(embed=True)`` 被忽略，每字段独立嵌入。"""

    @router.post("/multi-embed")
    class MultiEmbed(APIRoute[dict[str, Any]]):
        a: Annotated[str, Body(embed=True)]
        b: Annotated[int, Body(embed=True)]

    body = _serialize_body_params(
        MultiEmbed(a="x", b=1),
        MultiEmbed._get_dependant(),
    )
    # 多 body 时 embed 被忽略，每个独立命名
    assert body.raw_data is not None
    assert body.raw_data.value == {"a": "x", "b": 1}


# ===== RequestBodyKind / RequestBody 字段约束（契约）=====


def test_request_body_kind_raw_enum() -> None:
    """``RequestBodyKind.RAW`` 存在，``RequestBodyKind.JSON`` 不存在。"""
    assert hasattr(RequestBodyKind, "RAW")
    assert not hasattr(RequestBodyKind, "JSON")


def test_request_body_field_names() -> None:
    """``RequestBody`` 字段名：``raw_data`` / ``binary_file`` 存在；``json_body`` / ``binary_body`` 不存在。"""
    from stoma.dependencies.request import RequestBody

    assert "raw_data" in RequestBody.__dataclass_fields__
    assert "binary_file" in RequestBody.__dataclass_fields__
    assert "json_body" not in RequestBody.__dataclass_fields__
    assert "binary_body" not in RequestBody.__dataclass_fields__


# ===== APIRouter.prefix 支持 =====


class TestAPIRouterPrefix:
    """APIRouter.prefix 构造参数 + 8 个方法自动 prepend 前缀的契约测试。"""

    def test_default_empty_prefix_unchanged(self) -> None:
        """默认构造（``prefix=""``）时，endpoint 路径不被改写。"""

        router_no_prefix = APIRouter()

        @router_no_prefix.get("/users")
        class GetUsers(APIRoute[list[UserData]]):
            limit: Annotated[int, Query()] = 20

        dependant = GetUsers._get_dependant()

        assert dependant.path == "/users"
        assert dependant.method == "GET"

    def test_prefix_prepended_to_path(self) -> None:
        """``APIRouter(prefix="/api/v3")`` 会把 prefix 拼到 path 前面。"""

        router_v3 = APIRouter(prefix="/api/v3")

        @router_v3.get("/store/inventory")
        class GetInventory(APIRoute[dict]):
            pass

        dependant = GetInventory._get_dependant()

        assert dependant.path == "/api/v3/store/inventory"
        assert dependant.method == "GET"

    def test_two_routers_different_prefixes_isolated(self) -> None:
        """两个不同 prefix 的 router 装饰不同 endpoint，路径互不污染。"""

        router_v1 = APIRouter(prefix="/api/v1")
        router_v2 = APIRouter(prefix="/api/v2")

        @router_v1.get("/users")
        class GetUsersV1(APIRoute[list[UserData]]):
            pass

        @router_v2.post("/users")
        class CreateUserV2(APIRoute[UserData]):
            name: str
            email: str

        dep_v1 = GetUsersV1._get_dependant()
        dep_v2 = CreateUserV2._get_dependant()

        assert dep_v1.path == "/api/v1/users"
        assert dep_v1.method == "GET"
        assert dep_v2.path == "/api/v2/users"
        assert dep_v2.method == "POST"
        assert dep_v1 is not dep_v2

    def test_prefix_with_path_param(self) -> None:
        """prefix 与路径参数共存：``path`` 完整拼接 + ``path_params`` 仍识别 ``{id}``。"""

        router_v3 = APIRouter(prefix="/api/v3")

        @router_v3.get("/users/{id}")
        class GetUserById(APIRoute[UserData]):
            id: int

        dependant = GetUserById._get_dependant()

        assert dependant.path == "/api/v3/users/{id}"
        assert dependant.method == "GET"
        assert len(dependant.path_params) == 1
        assert dependant.path_params[0].alias == "id"


# 旧 ``test_client_helpers.py`` 里的 ``TestFillScalarFormField`` 已迁到
# :mod:`tests.unit.dependencies.test_request` 的 ``_fill_form_data`` 单测下。


# ===== APIRoute.__init_subclass__ 保留字段名校验 =====


class _ReservedRouteModel(BaseModel):
    """保留字段校验测试用的 Pydantic 模型。"""

    name: str
    age: int = 0


def test_reserved_field_names_rejected_int() -> None:
    """``on_200: int = 200`` 在类定义时立即抛 ``ValueError``。

    错误信息需包含字段名 ``on_200`` 与 ``reserved keyword`` 字样。
    """

    with pytest.raises(ValueError, match=r"on_200.*reserved keyword|reserved keyword.*on_200"):

        class BadRoute(APIRoute):
            on_200: int = 200


def test_reserved_field_names_rejected_default() -> None:
    """``on_default: str = ""`` 在类定义时立即抛 ``ValueError``。"""

    with pytest.raises(ValueError, match=r"on_default.*reserved keyword|reserved keyword.*on_default"):

        class BadDefault(APIRoute):
            on_default: str = ""


def test_reserved_field_names_rejected_4xx_wildcard() -> None:
    """``on_4xx``（OpenAPI 4XX 通配符）在类定义时抛 ``ValueError``。"""

    with pytest.raises(ValueError, match=r"on_4xx.*reserved keyword|reserved keyword.*on_4xx"):

        class BadWildcard4xx(APIRoute):
            on_4xx: int = 400


def test_reserved_field_names_rejected_5xx_wildcard() -> None:
    """``on_5xx``（OpenAPI 5XX 通配符）在类定义时抛 ``ValueError``。"""

    with pytest.raises(ValueError, match=r"on_5xx.*reserved keyword|reserved keyword.*on_5xx"):

        class BadWildcard5xx(APIRoute):
            on_5xx: str = ""


def test_reserved_field_names_rejected_multi_media() -> None:
    """``on_200_application_json``（多 media type 消歧后缀）在类定义时抛 ``ValueError``。"""

    with pytest.raises(
        ValueError,
        match=r"on_200_application_json.*reserved keyword|reserved keyword.*on_200_application_json",
    ):

        class BadMultiMedia(APIRoute):
            on_200_application_json: int = 200


def test_classvar_on_allowed() -> None:
    """``on_200: ClassVar = JSONResponseSpec(200, Model)`` 不抛错（渲染器生成的合法代码）。

    ``on_*`` 字段绑定到 :class:`BaseResponseSpec` 实例时，校验跳过；
    这是渲染器生成 endpoint 文件时的合法模式（``tests/examples/**/app/endpoints/*.py``）。
    """

    from stoma.dependencies.response import JSONResponseSpec

    class GeneratedRoute(APIRoute):
        on_200: ClassVar = JSONResponseSpec(200, "application/json", _ReservedRouteModel)

    # 类定义不抛错；实例化正常
    endpoint = GeneratedRoute()
    assert endpoint is not None
    assert isinstance(GeneratedRoute.on_200, JSONResponseSpec)
    assert GeneratedRoute.on_200.status_code == 200


def test_normal_field_names_allowed() -> None:
    """普通字段名（``user_id``、``limit``、``name``、``status``、``body`` 等）不抛错。"""

    class NormalRoute(APIRoute):
        user_id: int
        limit: int = 10
        name: str = "default"
        status: str = "active"

    endpoint = NormalRoute(user_id=1)
    assert endpoint.user_id == 1
    assert endpoint.limit == 10
    assert endpoint.name == "default"
    assert endpoint.status == "active"
