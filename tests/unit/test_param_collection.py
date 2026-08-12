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

import pathlib
from typing import Annotated, Any

import pytest
from playwright.sync_api import FormData
from pydantic import BaseModel, Field

from src.client import Client, RequestBodyKind
from src import Body, Form, Header, Path, Query, UploadFile
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
        page_num: Annotated[int, Query(), Field(serialization_alias="pageNum", default=1)]

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


def test_form_scalar_passes_value() -> None:
    """测试 Form 标量字段值原值存储（不 ``json.dumps``），与 FastAPI ``Form()`` 直传字符串一致。"""

    @router.post("/form-scalar")
    class LoginForm(APIRoute[dict[str, Any]]):
        username: Annotated[str, Form()]

    endpoint = LoginForm(username="alice")
    body = Client(context=None)._serialize_body_params(endpoint, endpoint._get_dependant())
    assert body.kind is RequestBodyKind.URLENCODED
    assert isinstance(body.form_data, FormData)
    assert body.form_data._fields == [("username", "alice")]


def test_form_int() -> None:
    """测试 Form 整数字段值原值存储（不 ``json.dumps``）。"""

    @router.post("/form-int")
    class AgeForm(APIRoute[dict[str, Any]]):
        age: Annotated[int, Form()]

    endpoint = AgeForm(age=42)
    body = Client(context=None)._serialize_body_params(endpoint, endpoint._get_dependant())
    assert body.kind is RequestBodyKind.URLENCODED
    assert isinstance(body.form_data, FormData)
    assert body.form_data._fields == [("age", 42)]


def test_form_scalar_list_append_multiple() -> None:
    """测试函数级 Form 列表值按元素追加同名字段。"""

    @router.post("/form-list")
    class TagsForm(APIRoute[dict[str, Any]]):
        tags: Annotated[list[str], Form()]

    endpoint = TagsForm(tags=["a", "b"])
    body = Client(context=None)._serialize_body_params(endpoint, endpoint._get_dependant())
    assert body.kind is RequestBodyKind.URLENCODED
    assert isinstance(body.form_data, FormData)
    assert body.form_data._fields == [("tags", "a"), ("tags", "b")]


def test_form_scalar_list_field() -> None:
    """测试函数级 Annotated[list[str], Form()] 追加多个同名字段。"""

    @router.post("/form-scalar-list-field")
    class ScalarListForm(APIRoute[dict[str, Any]]):
        tags: Annotated[list[str], Form()]

    endpoint = ScalarListForm(tags=["a", "b"])
    body = Client(context=None)._serialize_body_params(endpoint, endpoint._get_dependant())
    assert body.kind is RequestBodyKind.URLENCODED
    assert isinstance(body.form_data, FormData)
    assert body.form_data._fields == [("tags", "a"), ("tags", "b")]


def test_form_bytes_annotation_raises_in_routing() -> None:
    """``Annotated[bytes, Form()]`` 在路由分类阶段抛 ``ValueError``。

    Playwright ``FormDataValue`` 不含 ``bytes``，因此 Form 在 ``src.routing`` 分类阶段
    直接拒绝该注解，错误消息提示用户 ``json.dumps`` 为 ``str`` 后传入或改用 ``UploadFile``。
    """

    class BytesFormEndpoint(APIRoute[dict[str, Any]]):
        """含 bytes Form 字段的路由类。"""

        payload: Annotated[bytes, Form()]

    with pytest.raises(ValueError, match=r"Form 不支持的字段类型.*json\.dumps"):
        BytesFormEndpoint._get_dependant(method="POST", path="/form-bytes")


def test_form_basemodel_raises_in_routing() -> None:
    """``Annotated[BaseModel, Form()]`` 在路由分类阶段抛 ``ValueError``。

    验证 ``Form`` 仅接受标量注解，``BaseModel`` 子字段路由期被拦截。
    不使用 ``@router.post`` 装饰器（装饰期就会触发 raise，绕过断言），
    改为直接调用 ``_get_dependant()`` 确保 raise 发生在调用期。
    """

    class SubmitFormEndpoint(APIRoute[dict[str, Any]]):
        """含 BaseModel Form 字段的路由类。"""

        data: Annotated[UserCreateRequest, Form()]

    with pytest.raises(ValueError, match="Form 不支持的字段类型"):
        SubmitFormEndpoint._get_dependant(method="POST", path="/submit")


def test_form_embed_kwarg_removed_raises_type_error() -> None:
    """测试 Form 不再接受 embed 关键字参数。"""

    with pytest.raises(TypeError, match="embed"):
        Form(embed=True)


def test_uploadfile_single(tmp_path: pathlib.Path) -> None:
    """测试单 ``UploadFile`` 走 multipart，``form_data`` 是 ``FormData`` 且包含文件路径。"""

    file_path = tmp_path / "test.txt"
    file_path.write_text("hello", encoding="utf-8")

    @router.post("/upload-single")
    class UploadSingle(APIRoute[dict[str, Any]]):
        file: UploadFile

    endpoint = UploadSingle(file=UploadFile(path=file_path))
    body = Client(context=None)._serialize_body_params(endpoint, endpoint._get_dependant())
    assert body.kind is RequestBodyKind.MULTIPART
    assert isinstance(body.form_data, FormData)
    assert body.form_data._fields == [("file", file_path)]


def test_uploadfile_list(tmp_path: pathlib.Path) -> None:
    """测试 ``list[UploadFile]`` 多文件走 multipart，``FormData`` 多次 ``append`` 同一 alias。"""

    file1 = tmp_path / "f1.txt"
    file2 = tmp_path / "f2.txt"
    file1.write_text("a", encoding="utf-8")
    file2.write_text("b", encoding="utf-8")

    @router.post("/upload-list")
    class UploadList(APIRoute[dict[str, Any]]):
        files: list[UploadFile]

    endpoint = UploadList(files=[UploadFile(path=file1), UploadFile(path=file2)])
    body = Client(context=None)._serialize_body_params(endpoint, endpoint._get_dependant())
    assert body.kind is RequestBodyKind.MULTIPART
    assert isinstance(body.form_data, FormData)
    assert body.form_data._fields == [("files", file1), ("files", file2)]


def test_uploadfile_optional_none() -> None:
    """``file: UploadFile | None = None`` + ``file=None`` → MULTIPART，``form_data`` 为空（跳过 None）。"""

    @router.post("/upload-opt-none")
    class UploadOptNone(APIRoute[dict[str, Any]]):
        file: UploadFile | None = None

    endpoint = UploadOptNone(file=None)
    body = Client(context=None)._serialize_body_params(endpoint, endpoint._get_dependant())
    assert body.kind is RequestBodyKind.MULTIPART
    assert isinstance(body.form_data, FormData)
    assert body.form_data._fields == []


def test_uploadfile_optional_missing() -> None:
    """``file: UploadFile | None = None`` + 构造时不传 → MULTIPART，``form_data`` 为空（缺省值 None 跳过）。"""

    @router.post("/upload-opt-missing")
    class UploadOptMissing(APIRoute[dict[str, Any]]):
        file: UploadFile | None = None

    endpoint = UploadOptMissing()  # 缺省值 None
    body = Client(context=None)._serialize_body_params(endpoint, endpoint._get_dependant())
    assert body.kind is RequestBodyKind.MULTIPART
    assert isinstance(body.form_data, FormData)
    assert body.form_data._fields == []


def test_uploadfile_optional_with_value(tmp_path: pathlib.Path) -> None:
    """``file: UploadFile | None = None`` + ``file=UploadFile(...)`` → MULTIPART，含单个文件 part。"""

    file_path = tmp_path / "opt.txt"
    file_path.write_text("optional content", encoding="utf-8")

    @router.post("/upload-opt-value")
    class UploadOptValue(APIRoute[dict[str, Any]]):
        file: UploadFile | None = None

    endpoint = UploadOptValue(file=UploadFile(path=file_path))
    body = Client(context=None)._serialize_body_params(endpoint, endpoint._get_dependant())
    assert body.kind is RequestBodyKind.MULTIPART
    assert isinstance(body.form_data, FormData)
    assert body.form_data._fields == [("file", file_path)]


def test_uploadfile_list_optional_none() -> None:
    """``files: list[UploadFile] | None = None`` + ``files=None`` → MULTIPART，``form_data`` 为空。"""

    @router.post("/upload-files-opt-none")
    class UploadFilesOptNone(APIRoute[dict[str, Any]]):
        files: list[UploadFile] | None = None

    endpoint = UploadFilesOptNone(files=None)
    body = Client(context=None)._serialize_body_params(endpoint, endpoint._get_dependant())
    assert body.kind is RequestBodyKind.MULTIPART
    assert isinstance(body.form_data, FormData)
    assert body.form_data._fields == []


def test_uploadfile_list_optional_empty() -> None:
    """``files: list[UploadFile] | None = None`` + ``files=[]`` → MULTIPART，``form_data`` 为空（空列表视为跳过）。"""

    @router.post("/upload-files-opt-empty")
    class UploadFilesOptEmpty(APIRoute[dict[str, Any]]):
        files: list[UploadFile] | None = None

    endpoint = UploadFilesOptEmpty(files=[])
    body = Client(context=None)._serialize_body_params(endpoint, endpoint._get_dependant())
    assert body.kind is RequestBodyKind.MULTIPART
    assert isinstance(body.form_data, FormData)
    assert body.form_data._fields == []


def test_pure_form_mutual_exclusion_raise() -> None:
    """测试 ``Body()`` 与 ``Form()`` 不能在同一 APIRoute 混用。"""
    with pytest.raises(ValueError, match="Body 与 Form/UploadFile 字段不能在同一 APIRoute 混用"):

        @router.post("/mixed")
        class MixedRoute(APIRoute[dict[str, Any]]):
            body: Annotated[dict[str, int], Body()]
            note: Annotated[str, Form()]


class TestUploadAsMultipartFlag:
    """upload_as_multipart=False 启动期校验。"""

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
        """list[UploadFile] + flag False → raise（list 包装不允许）。"""
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
        """UploadFile | None = None + flag False → 通过校验 + Dependant 正确。

        Plan 增强：raw-body 模式现在接受 UploadFile | None（裸 Optional）。
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
        """1 裸 UploadFile + flag False → 通过校验 + Dependant 正确。"""
        class R(APIRoute[dict]):
            file: UploadFile

        d = R._get_dependant(method="POST", path="/x", upload_as_multipart=False)
        assert d.upload_as_multipart is False
        assert len(d.file_body_params) == 1
        assert d.file_body_params[0].name == "file"

    def test_upload_as_multipart_default_true_passes(self) -> None:
        """默认值（不传 upload_as_multipart=True）允许裸 UploadFile。"""
        class R(APIRoute[dict]):
            file: UploadFile

        d = R._get_dependant(method="POST", path="/x")
        assert d.upload_as_multipart is True
        assert len(d.file_body_params) == 1
