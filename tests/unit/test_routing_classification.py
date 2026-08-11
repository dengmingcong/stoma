"""T2: 测试 Form-marked 文件类型路由分类。

验证行为矩阵（route 到 file_body_params vs form_body_params）：
- Annotated[UploadFile, Form()] → file_body_params（新行为，原本错误地落 form_body_params）
- Annotated[list[UploadFile], Form()] → file_body_params
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


def test_form_marked_uploadfile_raises() -> None:
    """Annotated[UploadFile, Form()] → ValueError。"""

    class UploadFileEndpoint(APIRoute[UserData]):
        file: Annotated[UploadFile, Form()]

    with pytest.raises(ValueError, match="Form 不支持的字段类型"):
        UploadFileEndpoint._get_dependant(method="POST", path="/upload")


def test_form_marked_list_uploadfile_raises() -> None:
    """Annotated[list[UploadFile], Form()] → ValueError。"""

    class UploadFilesEndpoint(APIRoute[UserData]):
        files: Annotated[list[UploadFile], Form()]

    with pytest.raises(ValueError, match="Form 不支持的字段类型"):
        UploadFilesEndpoint._get_dependant(method="POST", path="/upload")


def test_form_marked_path_raises() -> None:
    """Annotated[pathlib.Path, Form()] → ValueError。"""

    class UploadPathEndpoint(APIRoute[UserData]):
        file_path: Annotated[pathlib.Path, Form()]

    with pytest.raises(ValueError, match="Form 不支持的字段类型"):
        UploadPathEndpoint._get_dependant(method="POST", path="/upload")


# === Form-marked 非文件类型 → form_body_params（不变） ===


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


def test_form_scalar_optional() -> None:
    """Annotated[Optional[str], Form()] → form_body_params。"""

    @router.post("/submit")
    class SubmitOptionalStrEndpoint(APIRoute[UserData]):
        name: Annotated[Optional[str], Form()]

    categories = get_param_categories(SubmitOptionalStrEndpoint)
    assert "name" in categories["form_body_params"]
    assert "name" not in categories["file_body_params"]


def test_form_scalar_list_optional() -> None:
    """Annotated[Optional[list[str]], Form()] → form_body_params。"""

    @router.post("/submit")
    class SubmitOptionalStrListEndpoint(APIRoute[UserData]):
        tags: Annotated[Optional[list[str]], Form()]

    categories = get_param_categories(SubmitOptionalStrListEndpoint)
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
