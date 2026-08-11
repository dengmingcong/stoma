"""T2: 测试 Form-marked 文件类型路由分类。

验证行为矩阵（route 到 file_body_params vs form_body_params）：
- Annotated[UploadFile, Form()] → file_body_params（新行为，原本错误地落 form_body_params）
- Annotated[list[UploadFile], Form()] → file_body_params
- Annotated[pathlib.Path, Form()] → file_body_params
- Annotated[list[pathlib.Path], Form()] → file_body_params
- Annotated[Optional[pathlib.Path], Form()] → file_body_params
- Annotated[BaseModel, Form()] → form_body_params（不变）
- Annotated[str, Form()] → form_body_params（不变）
- Annotated[list[str], Form()] → form_body_params（不变）
- UploadFile（无 Form 标记）→ file_body_params（不变）
"""

import pathlib
from typing import Annotated, Any, Optional

import pytest
from pydantic import BaseModel

from src.params import Body, Form, Query, UploadFile
from src.routing import APIRoute, APIRouter


router = APIRouter()


class UserData(BaseModel):
    """用户数据模型。"""
    id: int
    name: str


class UserCreateRequest(BaseModel):
    """创建用户请求模型。"""
    name: str
    email: str


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


# === Form-marked 文件类型 → file_body_params（新增行为） ===


def test_form_marked_uploadfile_routes_to_file_body_params() -> None:
    """Annotated[UploadFile, Form()] → file_body_params（新行为）。"""

    @router.post("/upload")
    class UploadFileEndpoint(APIRoute[UserData]):
        file: Annotated[UploadFile, Form()]

    categories = get_param_categories(UploadFileEndpoint)
    assert "file" in categories["file_body_params"]
    assert "file" not in categories["form_body_params"]


def test_form_marked_list_uploadfile_routes_to_file_body_params() -> None:
    """Annotated[list[UploadFile], Form()] → file_body_params。"""

    @router.post("/upload")
    class UploadFilesEndpoint(APIRoute[UserData]):
        files: Annotated[list[UploadFile], Form()]

    categories = get_param_categories(UploadFilesEndpoint)
    assert "files" in categories["file_body_params"]
    assert "files" not in categories["form_body_params"]


def test_form_marked_path_routes_to_file_body_params() -> None:
    """Annotated[pathlib.Path, Form()] → file_body_params。"""

    @router.post("/upload")
    class UploadPathEndpoint(APIRoute[UserData]):
        file_path: Annotated[pathlib.Path, Form()]

    categories = get_param_categories(UploadPathEndpoint)
    assert "file_path" in categories["file_body_params"]
    assert "file_path" not in categories["form_body_params"]


def test_form_marked_list_path_routes_to_file_body_params() -> None:
    """Annotated[list[pathlib.Path], Form()] → file_body_params。"""

    @router.post("/upload")
    class UploadPathsEndpoint(APIRoute[UserData]):
        file_paths: Annotated[list[pathlib.Path], Form()]

    categories = get_param_categories(UploadPathsEndpoint)
    assert "file_paths" in categories["file_body_params"]
    assert "file_paths" not in categories["form_body_params"]


def test_form_marked_optional_path_routes_to_file_body_params() -> None:
    """Annotated[Optional[pathlib.Path], Form()] → file_body_params。"""

    @router.post("/upload")
    class UploadOptionalPathEndpoint(APIRoute[UserData]):
        file_path: Annotated[Optional[pathlib.Path], Form()]

    categories = get_param_categories(UploadOptionalPathEndpoint)
    assert "file_path" in categories["file_body_params"]
    assert "file_path" not in categories["form_body_params"]


# === Form-marked 非文件类型 → form_body_params（不变） ===


def test_form_marked_basemodel_routes_to_form_body_params() -> None:
    """Annotated[BaseModel, Form()] → form_body_params（不变）。"""

    @router.post("/submit")
    class SubmitFormEndpoint(APIRoute[UserData]):
        data: Annotated[UserCreateRequest, Form()]

    categories = get_param_categories(SubmitFormEndpoint)
    assert "data" in categories["form_body_params"]
    assert "data" not in categories["file_body_params"]
    assert "data" not in categories["pure_body_params"]


def test_form_marked_str_routes_to_form_body_params() -> None:
    """Annotated[str, Form()] → form_body_params（不变）。"""

    @router.post("/submit")
    class SubmitStrEndpoint(APIRoute[UserData]):
        name: Annotated[str, Form()]

    categories = get_param_categories(SubmitStrEndpoint)
    assert "name" in categories["form_body_params"]
    assert "name" not in categories["file_body_params"]


def test_form_marked_list_str_routes_to_form_body_params() -> None:
    """Annotated[list[str], Form()] → form_body_params（不变）。"""

    @router.post("/submit")
    class SubmitStrListEndpoint(APIRoute[UserData]):
        tags: Annotated[list[str], Form()]

    categories = get_param_categories(SubmitStrListEndpoint)
    assert "tags" in categories["form_body_params"]
    assert "tags" not in categories["file_body_params"]


# === 无 Form 标记的 UploadFile → file_body_params（不变） ===


def test_unmarked_uploadfile_routes_to_file_body_params() -> None:
    """UploadFile（无 Form 标记）→ file_body_params（不变）。"""

    @router.post("/upload")
    class UnmarkedUploadEndpoint(APIRoute[UserData]):
        file: UploadFile

    categories = get_param_categories(UnmarkedUploadEndpoint)
    assert "file" in categories["file_body_params"]
    assert "file" not in categories["form_body_params"]


# === 混用场景测试 ==='


def test_mixed_form_marked_params() -> None:
    """混用 Form-marked 文件类型和普通类型。"""

    @router.post("/mixed")
    class MixedEndpoint(APIRoute[UserData]):
        file: Annotated[UploadFile, Form()]
        name: Annotated[str, Form()]
        path: Annotated[pathlib.Path, Form()]

    categories = get_param_categories(MixedEndpoint)
    assert categories["file_body_params"] == ["file", "path"]
    assert categories["form_body_params"] == ["name"]


def test_form_basemodel_raises_in_routing() -> None:
    """Annotated[BaseModel, Form()] → ValueError（Form 不支持 BaseModel 子字段）。"""

    @router.post("/submit")
    class SubmitFormEndpoint(APIRoute[UserData]):
        data: Annotated[UserCreateRequest, Form()]

    with pytest.raises(ValueError, match="Form 不支持 BaseModel 子字段"):
        SubmitFormEndpoint._get_dependant(method="POST", path="/submit")
