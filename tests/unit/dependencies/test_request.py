"""``src.dependencies.request`` 的单元测试。

合并自以下历史文件：

- :mod:`tests.unit.test_param_collection` 的 Form / UploadFile / RawPayload 序列化
  与 ``Body(media_type)`` 行为（``upload_as_multipart=False`` 已在
  :mod:`tests.unit.test_routing`）。
- :mod:`tests.unit.test_client_helpers` —— ``_fill_form_data`` / ``_fill_scalar_form_field``
  基于 ``field_info.annotation`` 的派发。
- :mod:`tests.unit.test_path_interpolation` —— ``_interpolate_path_params``。
- :mod:`tests.unit.test_query_serialization` —— ``_collect_query_params``。
"""

import pathlib
from typing import Annotated, Any

from playwright.sync_api import FormData
from pydantic import BaseModel, Field
from pydantic.fields import FieldInfo

from stoma import Body, Form, JSONResponseSpec, Path, Query, UploadFile
from stoma.dependencies import ModelField
from stoma.dependencies.request import (
    RawPayload,
    RequestBodyKind,
    _collect_query_params,
    _fill_form_data,
    _interpolate_path_params,
    _serialize_body_params,
)
from stoma.routing import APIRoute, APIRouter

router = APIRouter()


# ===== 测试响应模型 =====


class UserData(BaseModel):
    """用户数据模型。"""

    id: int
    name: str
    email: str


# ===== Form 字段序列化 =====


def test_form_scalar_passes_value() -> None:
    """测试 Form 标量字段值原值存储（不 ``json.dumps``），与 FastAPI ``Form()`` 直传字符串一致。"""

    @router.post("/form-scalar")
    class LoginForm(APIRoute):
        username: Annotated[str, Form()]

        @property
        def on_201(self) -> JSONResponseSpec[dict[str, Any]]:
            return JSONResponseSpec(status_code=201, media_type="application/json", model=dict[str, Any])

    endpoint = LoginForm(username="alice")
    body = _serialize_body_params(endpoint, endpoint._get_dependant())
    assert body.kind is RequestBodyKind.URLENCODED_FORM
    assert isinstance(body.form_data, FormData)
    assert body.form_data._fields == [("username", "alice")]


def test_form_int() -> None:
    """测试 Form 整数字段值原值存储（不 ``json.dumps``）。"""

    @router.post("/form-int")
    class AgeForm(APIRoute):
        age: Annotated[int, Form()]

        @property
        def on_201(self) -> JSONResponseSpec[dict[str, Any]]:
            return JSONResponseSpec(status_code=201, media_type="application/json", model=dict[str, Any])

    endpoint = AgeForm(age=42)
    body = _serialize_body_params(endpoint, endpoint._get_dependant())
    assert body.kind is RequestBodyKind.URLENCODED_FORM
    assert isinstance(body.form_data, FormData)
    assert body.form_data._fields == [("age", 42)]


def test_form_scalar_list_append_multiple() -> None:
    """测试函数级 Form 列表值按元素追加同名字段。"""

    @router.post("/form-list")
    class TagsForm(APIRoute):
        tags: Annotated[list[str], Form()]

        @property
        def on_201(self) -> JSONResponseSpec[dict[str, Any]]:
            return JSONResponseSpec(status_code=201, media_type="application/json", model=dict[str, Any])

    endpoint = TagsForm(tags=["a", "b"])
    body = _serialize_body_params(endpoint, endpoint._get_dependant())
    assert body.kind is RequestBodyKind.URLENCODED_FORM
    assert isinstance(body.form_data, FormData)
    assert body.form_data._fields == [("tags", "a"), ("tags", "b")]


def test_form_scalar_list_field() -> None:
    """测试函数级 ``Annotated[list[str], Form()]`` 追加多个同名字段。"""

    @router.post("/form-scalar-list-field")
    class ScalarListForm(APIRoute):
        tags: Annotated[list[str], Form()]

        @property
        def on_201(self) -> JSONResponseSpec[dict[str, Any]]:
            return JSONResponseSpec(status_code=201, media_type="application/json", model=dict[str, Any])

    endpoint = ScalarListForm(tags=["a", "b"])
    body = _serialize_body_params(endpoint, endpoint._get_dependant())
    assert body.kind is RequestBodyKind.URLENCODED_FORM
    assert isinstance(body.form_data, FormData)
    assert body.form_data._fields == [("tags", "a"), ("tags", "b")]


# ===== UploadFile 字段序列化 =====


def test_uploadfile_single(tmp_path: pathlib.Path) -> None:
    """测试单 ``UploadFile`` 走 multipart，``form_data`` 是 ``FormData`` 且包含文件路径。"""

    file_path = tmp_path / "test.txt"
    file_path.write_text("hello", encoding="utf-8")

    @router.post("/upload-single")
    class UploadSingle(APIRoute):
        file: UploadFile

        @property
        def on_201(self) -> JSONResponseSpec[dict[str, Any]]:
            return JSONResponseSpec(status_code=201, media_type="application/json", model=dict[str, Any])

    endpoint = UploadSingle(file=UploadFile(path=file_path))
    body = _serialize_body_params(endpoint, endpoint._get_dependant())
    assert body.kind is RequestBodyKind.MULTIPART_FORM
    assert isinstance(body.form_data, FormData)
    assert body.form_data._fields == [("file", file_path)]


def test_uploadfile_list(tmp_path: pathlib.Path) -> None:
    """测试 ``list[UploadFile]`` 多文件走 multipart，``FormData`` 多次 ``append`` 同一 alias。"""

    file1 = tmp_path / "f1.txt"
    file2 = tmp_path / "f2.txt"
    file1.write_text("a", encoding="utf-8")
    file2.write_text("b", encoding="utf-8")

    @router.post("/upload-list")
    class UploadList(APIRoute):
        files: list[UploadFile]

        @property
        def on_201(self) -> JSONResponseSpec[dict[str, Any]]:
            return JSONResponseSpec(status_code=201, media_type="application/json", model=dict[str, Any])

    endpoint = UploadList(files=[UploadFile(path=file1), UploadFile(path=file2)])
    body = _serialize_body_params(endpoint, endpoint._get_dependant())
    assert body.kind is RequestBodyKind.MULTIPART_FORM
    assert isinstance(body.form_data, FormData)
    assert body.form_data._fields == [("files", file1), ("files", file2)]


def test_uploadfile_optional_none() -> None:
    """``file: UploadFile | None = None`` + ``file=None`` → MULTIPART，``form_data`` 为空（跳过 None）。"""

    @router.post("/upload-opt-none")
    class UploadOptNone(APIRoute):
        file: UploadFile | None = None

        @property
        def on_201(self) -> JSONResponseSpec[dict[str, Any]]:
            return JSONResponseSpec(status_code=201, media_type="application/json", model=dict[str, Any])

    endpoint = UploadOptNone(file=None)
    body = _serialize_body_params(endpoint, endpoint._get_dependant())
    assert body.kind is RequestBodyKind.MULTIPART_FORM
    assert isinstance(body.form_data, FormData)
    assert body.form_data._fields == []


def test_uploadfile_optional_missing() -> None:
    """``file: UploadFile | None = None`` + 构造时不传 → MULTIPART，``form_data`` 为空（缺省值 None 跳过）。"""

    @router.post("/upload-opt-missing")
    class UploadOptMissing(APIRoute):
        file: UploadFile | None = None

        @property
        def on_201(self) -> JSONResponseSpec[dict[str, Any]]:
            return JSONResponseSpec(status_code=201, media_type="application/json", model=dict[str, Any])

    endpoint = UploadOptMissing()  # 缺省值 None
    body = _serialize_body_params(endpoint, endpoint._get_dependant())
    assert body.kind is RequestBodyKind.MULTIPART_FORM
    assert isinstance(body.form_data, FormData)
    assert body.form_data._fields == []


def test_uploadfile_optional_with_value(tmp_path: pathlib.Path) -> None:
    """``file: UploadFile | None = None`` + ``file=UploadFile(...)`` → MULTIPART，含单个文件 part。"""

    file_path = tmp_path / "opt.txt"
    file_path.write_text("optional content", encoding="utf-8")

    @router.post("/upload-opt-value")
    class UploadOptValue(APIRoute):
        file: UploadFile | None = None

        @property
        def on_201(self) -> JSONResponseSpec[dict[str, Any]]:
            return JSONResponseSpec(status_code=201, media_type="application/json", model=dict[str, Any])

    endpoint = UploadOptValue(file=UploadFile(path=file_path))
    body = _serialize_body_params(endpoint, endpoint._get_dependant())
    assert body.kind is RequestBodyKind.MULTIPART_FORM
    assert isinstance(body.form_data, FormData)
    assert body.form_data._fields == [("file", file_path)]


def test_uploadfile_list_optional_none() -> None:
    """``files: list[UploadFile] | None = None`` + ``files=None`` → MULTIPART，``form_data`` 为空。"""

    @router.post("/upload-files-opt-none")
    class UploadFilesOptNone(APIRoute):
        files: list[UploadFile] | None = None

        @property
        def on_201(self) -> JSONResponseSpec[dict[str, Any]]:
            return JSONResponseSpec(status_code=201, media_type="application/json", model=dict[str, Any])

    endpoint = UploadFilesOptNone(files=None)
    body = _serialize_body_params(endpoint, endpoint._get_dependant())
    assert body.kind is RequestBodyKind.MULTIPART_FORM
    assert isinstance(body.form_data, FormData)
    assert body.form_data._fields == []


def test_uploadfile_list_optional_empty() -> None:
    """``files: list[UploadFile] | None = None`` + ``files=[]`` → MULTIPART，``form_data`` 为空（空列表视为跳过）。"""

    @router.post("/upload-files-opt-empty")
    class UploadFilesOptEmpty(APIRoute):
        files: list[UploadFile] | None = None

        @property
        def on_201(self) -> JSONResponseSpec[dict[str, Any]]:
            return JSONResponseSpec(status_code=201, media_type="application/json", model=dict[str, Any])

    endpoint = UploadFilesOptEmpty(files=[])
    body = _serialize_body_params(endpoint, endpoint._get_dependant())
    assert body.kind is RequestBodyKind.MULTIPART_FORM
    assert isinstance(body.form_data, FormData)
    assert body.form_data._fields == []


# ===== _fill_form_data 基于 field_info.annotation 的派发 =====


class TestFillScalarFormField:
    """``_fill_form_data`` 基于 ``field_info.annotation`` 的派发。"""

    @staticmethod
    def _fill(annotation: object, value: object) -> FormData:
        field_info = FieldInfo(annotation=annotation)
        model_field = ModelField(name="field", field_info=field_info, param_info=Form())
        form_data = FormData()
        _fill_form_data(form_data, model_field, value)
        return form_data

    def test_scalar_str_set(self) -> None:
        """``str`` 标量 → ``form_data.set`` 原值。"""
        assert self._fill(str, "alice")._fields == [("field", "alice")]

    def test_scalar_int_set(self) -> None:
        """``int`` 标量原值传递，不转 ``str``。"""
        assert self._fill(int, 42)._fields == [("field", 42)]

    def test_scalar_bool_set(self) -> None:
        """``bool`` 标量原值传递。"""
        assert self._fill(bool, True)._fields == [("field", True)]

    def test_none_skipped(self) -> None:
        """``None`` 值跳过，不产生任何 part。"""
        assert self._fill(str | None, None)._fields == []

    def test_list_text_appends_each(self) -> None:
        """``list[str]`` 每个元素 ``append`` 一次同名 part。"""
        assert self._fill(list[str], ["a", "b"])._fields == [("field", "a"), ("field", "b")]

    def test_list_text_skips_none_element(self) -> None:
        """``list`` 中的 ``None`` 元素跳过，其余照常 ``append``。"""
        assert self._fill(list[str], ["a", None, "b"])._fields == [("field", "a"), ("field", "b")]

    def test_empty_list_skipped(self) -> None:
        """空 ``list`` 不产生任何 part。"""
        assert self._fill(list[str], [])._fields == []


# ===== Body(media_type) 与 RawPayload =====


class TestRawPayloadAndMediaType:
    """``RawPayload`` / ``Body.media_type`` / Form 继承 / RAW enum 测试。"""

    def test_raw_payload_namedtuple(self) -> None:
        """``RawPayload`` 字段可访问。"""
        rp = RawPayload(value={"a": 1}, media_type="application/xml")
        assert rp.value == {"a": 1}
        assert rp.media_type == "application/xml"

    def test_raw_payload_media_type_optional(self) -> None:
        """``RawPayload.media_type`` 默认 None。"""
        rp = RawPayload(value=5)
        assert rp.value == 5
        assert rp.media_type is None

    def test_body_media_type_scalar_only(self) -> None:
        """``Body(media_type)`` 三条件全满足：scalar + embed=False + 1 body → media_type 设置。"""

        @router.post("/scalar-media")
        class ScalarMedia(APIRoute):
            value: Annotated[int, Body(media_type="text/plain")]

            @property
            def on_201(self) -> JSONResponseSpec[dict[str, Any]]:
                return JSONResponseSpec(status_code=201, media_type="application/json", model=dict[str, Any])

        body = _serialize_body_params(
            ScalarMedia(value=5),
            ScalarMedia._get_dependant(),
        )
        assert body.kind is RequestBodyKind.RAW
        assert body.raw_data is not None
        assert body.raw_data.value == 5
        assert body.raw_data.media_type == "text/plain"

    def test_body_media_type_default_none(self) -> None:
        """``Body()`` 不显式设 media_type → ``raw_data.media_type`` is None。"""

        @router.post("/scalar-default")
        class ScalarDefault(APIRoute):
            value: Annotated[int, Body()]

            @property
            def on_201(self) -> JSONResponseSpec[dict[str, Any]]:
                return JSONResponseSpec(status_code=201, media_type="application/json", model=dict[str, Any])

        body = _serialize_body_params(
            ScalarDefault(value=42),
            ScalarDefault._get_dependant(),
        )
        assert body.kind is RequestBodyKind.RAW
        assert body.raw_data is not None
        assert body.raw_data.value == 42
        assert body.raw_data.media_type is None

    def test_body_media_type_ignored_with_multiple_body_params(self) -> None:
        """多 body + media_type → media_type 被忽略。"""

        @router.post("/multi-media")
        class MultiMedia(APIRoute):
            name: Annotated[str, Body()]
            age: Annotated[int, Body(media_type="text/plain")]

            @property
            def on_201(self) -> JSONResponseSpec[dict[str, Any]]:
                return JSONResponseSpec(status_code=201, media_type="application/json", model=dict[str, Any])

        body = _serialize_body_params(
            MultiMedia(name="alice", age=30),
            MultiMedia._get_dependant(),
        )
        assert body.kind is RequestBodyKind.RAW
        assert body.raw_data is not None
        assert body.raw_data.media_type is None

    def test_body_media_type_ignored_when_embed_true(self) -> None:
        """``Body(embed=True, media_type=...)`` → media_type 被忽略。"""

        @router.post("/embed-media")
        class EmbedMedia(APIRoute):
            value: Annotated[int, Body(embed=True, media_type="text/plain")]

            @property
            def on_201(self) -> JSONResponseSpec[dict[str, Any]]:
                return JSONResponseSpec(status_code=201, media_type="application/json", model=dict[str, Any])

        body = _serialize_body_params(
            EmbedMedia(value=7),
            EmbedMedia._get_dependant(),
        )
        assert body.kind is RequestBodyKind.RAW
        assert body.raw_data is not None
        assert body.raw_data.media_type is None

    def test_body_media_type_ignored_for_basemodel(self) -> None:
        """``BaseModel`` + media_type → media_type 被忽略。"""

        class LocalUserCreateRequest(BaseModel):
            """本地创建用户请求模型。"""

            name: str
            email: str

        @router.post("/basemodel-media")
        class BM(APIRoute):
            data: Annotated[LocalUserCreateRequest, Body(media_type="application/xml")]

            @property
            def on_201(self) -> JSONResponseSpec[dict[str, Any]]:
                return JSONResponseSpec(status_code=201, media_type="application/json", model=dict[str, Any])

        body = _serialize_body_params(
            BM(data=LocalUserCreateRequest(name="x", email="y@z.com")),
            BM._get_dependant(),
        )
        assert body.kind is RequestBodyKind.RAW
        assert body.raw_data is not None
        assert body.raw_data.media_type is None

    def test_body_media_type_ignored_for_list(self) -> None:
        """``list[T]`` + media_type → media_type 被忽略（list 非标量）。"""

        @router.post("/list-media")
        class ListMedia(APIRoute):
            values: Annotated[list[int], Body(media_type="text/plain")]

            @property
            def on_201(self) -> JSONResponseSpec[dict[str, Any]]:
                return JSONResponseSpec(status_code=201, media_type="application/json", model=dict[str, Any])

        body = _serialize_body_params(
            ListMedia(values=[1, 2, 3]),
            ListMedia._get_dependant(),
        )
        assert body.kind is RequestBodyKind.RAW
        assert body.raw_data is not None
        assert body.raw_data.media_type is None

    def test_raw_data_scalar_value(self) -> None:
        """scalar ``Body()`` → ``raw_data.value`` 是裸值。"""

        @router.post("/scalar-bare")
        class ScalarBare(APIRoute):
            importance: Annotated[int, Body()]

            @property
            def on_201(self) -> JSONResponseSpec[dict[str, Any]]:
                return JSONResponseSpec(status_code=201, media_type="application/json", model=dict[str, Any])

        body = _serialize_body_params(
            ScalarBare(importance=99),
            ScalarBare._get_dependant(),
        )
        assert body.raw_data is not None
        assert body.raw_data.value == 99  # 裸值，不是 dict

    def test_raw_data_scalar_no_embed(self) -> None:
        """scalar ``Body(embed=False)`` → ``raw_data.value`` 是裸值。"""

        @router.post("/scalar-no-embed")
        class ScalarNoEmbed(APIRoute):
            importance: Annotated[int, Body(embed=False)]

            @property
            def on_201(self) -> JSONResponseSpec[dict[str, Any]]:
                return JSONResponseSpec(status_code=201, media_type="application/json", model=dict[str, Any])

        body = _serialize_body_params(
            ScalarNoEmbed(importance=10),
            ScalarNoEmbed._get_dependant(),
        )
        assert body.raw_data is not None
        assert body.raw_data.value == 10

    def test_raw_data_dict_value_default_no_media_type(self) -> None:
        """``BaseModel`` + no media_type → ``raw_data.value`` is dict, media_type None。"""

        class LocalUserCreateRequest(BaseModel):
            """本地创建用户请求模型。"""

            name: str
            email: str

        @router.post("/bm-default")
        class BMDefault(APIRoute):
            data: LocalUserCreateRequest

            @property
            def on_201(self) -> JSONResponseSpec[dict[str, Any]]:
                return JSONResponseSpec(status_code=201, media_type="application/json", model=dict[str, Any])

        body = _serialize_body_params(
            BMDefault(data=LocalUserCreateRequest(name="alice", email="a@b.com")),
            BMDefault._get_dependant(),
        )
        assert body.raw_data is not None
        assert isinstance(body.raw_data.value, dict)
        assert body.raw_data.value["name"] == "alice"
        assert body.raw_data.media_type is None


# ===== 路径参数插值 =====


def test_interpolate_single_path_param() -> None:
    """测试单个路径参数的插值。"""

    @router.get("/users/{user_id}")
    class GetUser(APIRoute):
        user_id: Annotated[int, Path()]

        @property
        def on_200(self) -> JSONResponseSpec[UserData]:
            return JSONResponseSpec(status_code=200, media_type="application/json", model=UserData)

    endpoint = GetUser(user_id=123)
    interpolated_path = _interpolate_path_params(endpoint, endpoint._get_dependant())

    assert interpolated_path == "/users/123"


def test_interpolate_multiple_path_params() -> None:
    """测试多个路径参数的插值。"""

    @router.get("/users/{user_id}/posts/{post_id}")
    class GetUserPost(APIRoute):
        user_id: Annotated[int, Path()]
        post_id: Annotated[int, Path()]

        @property
        def on_200(self) -> JSONResponseSpec[dict[str, str]]:
            return JSONResponseSpec(status_code=200, media_type="application/json", model=dict[str, str])

    endpoint = GetUserPost(user_id=123, post_id=456)
    interpolated_path = _interpolate_path_params(endpoint, endpoint._get_dependant())

    assert interpolated_path == "/users/123/posts/456"


def test_interpolate_path_with_string_param() -> None:
    """测试携带字符串参数的路径插值。"""

    @router.get("/posts/{slug}/comments/{comment_id}")
    class GetPostComment(APIRoute):
        slug: Annotated[str, Path()]
        comment_id: Annotated[int, Path()]

        @property
        def on_200(self) -> JSONResponseSpec[dict[str, str]]:
            return JSONResponseSpec(status_code=200, media_type="application/json", model=dict[str, str])

    endpoint = GetPostComment(slug="hello-world", comment_id=789)
    interpolated_path = _interpolate_path_params(endpoint, endpoint._get_dependant())

    assert interpolated_path == "/posts/hello-world/comments/789"


def test_interpolate_path_with_mixed_params() -> None:
    """测试混合参数类型的路径插值。"""

    @router.put("/users/{user_id}/resource/{resource_id}/version/{version}")
    class UpdateResource(APIRoute):
        user_id: Annotated[int, Path()]
        resource_id: Annotated[str, Path()]
        version: Annotated[int, Path()]

        @property
        def on_200(self) -> JSONResponseSpec[dict[str, str]]:
            return JSONResponseSpec(status_code=200, media_type="application/json", model=dict[str, str])

    endpoint = UpdateResource(user_id=42, resource_id="abc123", version=2)
    interpolated_path = _interpolate_path_params(endpoint, endpoint._get_dependant())

    assert interpolated_path == "/users/42/resource/abc123/version/2"


def test_interpolate_path_no_params() -> None:
    """测试没有路径参数的路径插值（应返回原始路径）。"""

    @router.get("/users")
    class ListUsers(APIRoute):
        limit: int = 20
        offset: int = 0

        @property
        def on_200(self) -> JSONResponseSpec[list[UserData]]:
            return JSONResponseSpec(status_code=200, media_type="application/json", model=list[UserData])

    endpoint = ListUsers(limit=10, offset=5)
    interpolated_path = _interpolate_path_params(endpoint, endpoint._get_dependant())

    assert interpolated_path == "/users"


def test_interpolate_path_preserves_base_path() -> None:
    """测试路径插值保留基础路径部分。"""

    @router.get("/api/v1/users/{user_id}")
    class GetUserV1(APIRoute):
        user_id: Annotated[int, Path()]

        @property
        def on_200(self) -> JSONResponseSpec[UserData]:
            return JSONResponseSpec(status_code=200, media_type="application/json", model=UserData)

    endpoint = GetUserV1(user_id=999)
    interpolated_path = _interpolate_path_params(endpoint, endpoint._get_dependant())

    assert interpolated_path == "/api/v1/users/999"


# ===== 查询参数序列化 =====


def test_serialize_single_query_param() -> None:
    """测试单个查询参数的序列化。"""

    @router.get("/users")
    class GetUsers(APIRoute):
        limit: Annotated[int, Query()] = 20

        @property
        def on_200(self) -> JSONResponseSpec[list[UserData]]:
            return JSONResponseSpec(status_code=200, media_type="application/json", model=list[UserData])

    endpoint = GetUsers(limit=10)
    query_params = _collect_query_params(endpoint, endpoint._get_dependant())

    assert query_params == {"limit": 10}


def test_serialize_multiple_query_params() -> None:
    """测试多个查询参数的序列化。"""

    @router.get("/users")
    class GetUsers(APIRoute):
        limit: Annotated[int, Query()] = 20
        offset: Annotated[int, Query()] = 0
        keyword: Annotated[str | None, Query()] = None

        @property
        def on_200(self) -> JSONResponseSpec[list[UserData]]:
            return JSONResponseSpec(status_code=200, media_type="application/json", model=list[UserData])

    endpoint = GetUsers(limit=50, offset=10, keyword="test")
    query_params = _collect_query_params(endpoint, endpoint._get_dependant())

    # Playwright 在发送时会自动 str() 转换 int，bool 转 'true'/'false'
    assert query_params == {"limit": 50, "offset": 10, "keyword": "test"}


def test_serialize_query_params_skip_none() -> None:
    """测试查询参数序列化时跳过 ``None`` 值。"""

    @router.get("/search")
    class Search(APIRoute):
        query: Annotated[str, Query()]
        limit: Annotated[int, Query()] = 20
        filter_type: Annotated[str | None, Query()] = None

        @property
        def on_200(self) -> JSONResponseSpec[list[UserData]]:
            return JSONResponseSpec(status_code=200, media_type="application/json", model=list[UserData])

    endpoint = Search(query="hello", limit=25, filter_type=None)
    query_params = _collect_query_params(endpoint, endpoint._get_dependant())

    # ``filter_type`` 应该被跳过（None）
    assert query_params == {"query": "hello", "limit": 25}
    assert "filter_type" not in query_params


def test_serialize_query_params_with_alias() -> None:
    """测试查询参数序列化时使用别名。"""

    @router.get("/users")
    class GetUsers(APIRoute):
        page_size: Annotated[int, Query()] = Field(serialization_alias="pageSize", default=20)
        page_num: Annotated[int, Query()] = Field(serialization_alias="pageNum", default=1)

        @property
        def on_200(self) -> JSONResponseSpec[list[UserData]]:
            return JSONResponseSpec(status_code=200, media_type="application/json", model=list[UserData])

    endpoint = GetUsers(page_size=50, page_num=2)
    query_params = _collect_query_params(endpoint, endpoint._get_dependant())

    # 应该使用别名作为键
    assert query_params == {"pageSize": 50, "pageNum": 2}


def test_serialize_query_params_with_boolean() -> None:
    """测试查询参数序列化时处理布尔值（HTTP 约定小写）。"""

    @router.get("/users")
    class GetUsers(APIRoute):
        active: Annotated[bool, Query()] = True
        verified: Annotated[bool, Query()] = False

        @property
        def on_200(self) -> JSONResponseSpec[list[UserData]]:
            return JSONResponseSpec(status_code=200, media_type="application/json", model=list[UserData])

    endpoint = GetUsers(active=True, verified=False)
    query_params = _collect_query_params(endpoint, endpoint._get_dependant())

    # bool 直接传递，Playwright 自动转换
    assert query_params == {"active": True, "verified": False}


def test_serialize_query_params_with_default_values() -> None:
    """测试查询参数序列化时使用默认值。"""

    @router.get("/users")
    class GetUsers(APIRoute):
        limit: Annotated[int, Query()] = 20
        offset: Annotated[int, Query()] = 0

        @property
        def on_200(self) -> JSONResponseSpec[list[UserData]]:
            return JSONResponseSpec(status_code=200, media_type="application/json", model=list[UserData])

    endpoint = GetUsers()
    query_params = _collect_query_params(endpoint, endpoint._get_dependant())

    # 默认值直接传递，Playwright 自动 str() 转换
    assert query_params == {"limit": 20, "offset": 0}


def test_serialize_query_params_type_conversion() -> None:
    """测试查询参数：int/float/str 直接传递（Playwright 自动 str()）。"""

    @router.get("/data")
    class GetData(APIRoute):
        count: Annotated[int, Query()] = 1
        ratio: Annotated[float, Query()] = 1.5
        name: Annotated[str, Query()] = "default"

        @property
        def on_200(self) -> JSONResponseSpec[dict]:
            return JSONResponseSpec(status_code=200, media_type="application/json", model=dict)

    endpoint = GetData(count=42, ratio=3.14, name="test")
    query_params = _collect_query_params(endpoint, endpoint._get_dependant())

    # int/float/str 直接传递，不做 str() 转换
    assert query_params == {"count": 42, "ratio": 3.14, "name": "test"}
