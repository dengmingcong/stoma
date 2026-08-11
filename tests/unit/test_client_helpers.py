"""T3: client.py 5 个 form 派发辅助函数的单元测试。"""

import pathlib
from typing import Annotated, Optional

import pytest
from pydantic import BaseModel
from playwright.sync_api import FormData

from src.client import (
    _classify_field_kind,
    _endpoint_form_mutex_violation,
    _fill_scalar_form_field,
    _is_basemodel_form_field,
    _is_pathlib_path_annotation,
)
from src.dependencies import Dependant, ModelField
from src.params import Body, Form, Query
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


# ============================================================
# _classify_field_kind
# ============================================================


class TestClassifyFieldKind:
    """测试 _classify_field_kind。"""

    def test_scalar_str(self) -> None:
        """标量类型 → ("scalar", annotation)。"""
        assert _classify_field_kind(str) == ("scalar", str)

    def test_scalar_int(self) -> None:
        """int → ("scalar", int)。"""
        assert _classify_field_kind(int) == ("scalar", int)

    def test_list_str(self) -> None:
        """list[str] → ("list", str)。"""
        assert _classify_field_kind(list[str]) == ("list", str)

    def test_optional_list_str(self) -> None:
        """Optional[list[str]] → ("list", str)。"""
        assert _classify_field_kind(Optional[list[str]]) == ("list", str)

    def test_annotated_list_str(self) -> None:
        """Annotated[list[str], Form()] → ("list", str)。"""
        assert _classify_field_kind(Annotated[list[str], Form()]) == ("list", str)

    def test_annotated_optional_list_str(self) -> None:
        """Annotated[Optional[list[str]], Form()] → ("list", str)。"""
        assert _classify_field_kind(Annotated[Optional[list[str]], Form()]) == ("list", str)

    def test_annotated_list_without_type_arg_raises(self) -> None:
        """Annotated[list, Form()] → ValueError（不是 IndexError）。"""
        with pytest.raises(ValueError, match="无法解析"):
            _classify_field_kind(Annotated[list, Form()])

    def test_union_none_str(self) -> None:
        """str | None → ("scalar", str | None)（视为标量）。"""
        result = _classify_field_kind(str | None)
        assert result[0] == "scalar"

    def test_annotated_annotated(self) -> None:
        """嵌套 Annotated → 递归解包。"""
        assert _classify_field_kind(Annotated[Annotated[str, Form()], Query()]) == (
            "scalar",
            str,
        )


# ============================================================
# _is_basemodel_form_field
# ============================================================


class TestIsBasemodelFormField:
    """测试 _is_basemodel_form_field。"""

    def _make_model_field(
        self, annotation: type, param_info: Form | Body | Query | None
    ) -> ModelField:
        """构造 ModelField 的辅助方法。"""
        from pydantic.fields import FieldInfo

        field_info = FieldInfo(annotation=annotation)
        return ModelField(name="test", field_info=field_info, param_info=param_info)

    def test_basemodel_form_true(self) -> None:
        """BaseModel + Form → True。"""
        field = self._make_model_field(UserCreateRequest, Form())
        assert _is_basemodel_form_field(field) is True

    def test_basemodel_body_false(self) -> None:
        """BaseModel + Body → False。"""
        field = self._make_model_field(UserCreateRequest, Body())
        assert _is_basemodel_form_field(field) is False

    def test_basemodel_query_false(self) -> None:
        """BaseModel + Query → False。"""
        field = self._make_model_field(UserCreateRequest, Query())
        assert _is_basemodel_form_field(field) is False

    def test_basemodel_no_param_false(self) -> None:
        """BaseModel + 无 param_info → False。"""
        field = self._make_model_field(UserCreateRequest, None)
        assert _is_basemodel_form_field(field) is False

    def test_str_form_false(self) -> None:
        """str + Form → False。"""
        field = self._make_model_field(str, Form())
        assert _is_basemodel_form_field(field) is False

    def test_list_basemodel_form_true(self) -> None:
        """list[BaseModel] + Form → False（list 不是 BaseModel 子类）。"""
        field = self._make_model_field(list[UserCreateRequest], Form())
        assert _is_basemodel_form_field(field) is False


# ============================================================
# _is_pathlib_path_annotation
# ============================================================


class TestIsPathlibPathAnnotation:
    """测试 _is_pathlib_path_annotation。"""

    def test_path_direct_true(self) -> None:
        """pathlib.Path → True。"""
        assert _is_pathlib_path_annotation(pathlib.Path) is True

    def test_optional_path_true(self) -> None:
        """Optional[pathlib.Path] → True。"""
        assert _is_pathlib_path_annotation(Optional[pathlib.Path]) is True

    def test_list_path_true(self) -> None:
        """list[pathlib.Path] → True。"""
        assert _is_pathlib_path_annotation(list[pathlib.Path]) is True

    def test_optional_list_path_true(self) -> None:
        """Optional[list[pathlib.Path]] → True。"""
        assert _is_pathlib_path_annotation(Optional[list[pathlib.Path]]) is True

    def test_annotated_path_true(self) -> None:
        """Annotated[pathlib.Path, "foo"] → True。"""
        assert _is_pathlib_path_annotation(Annotated[pathlib.Path, "foo"]) is True

    def test_str_false(self) -> None:
        """str → False。"""
        assert _is_pathlib_path_annotation(str) is False

    def test_int_false(self) -> None:
        """int → False。"""
        assert _is_pathlib_path_annotation(int) is False

    def test_purepath_false(self) -> None:
        """pathlib.PurePath（父类）→ False。"""
        assert _is_pathlib_path_annotation(pathlib.PurePath) is False

    def test_list_str_false(self) -> None:
        """list[str] → False。"""
        assert _is_pathlib_path_annotation(list[str]) is False

    def test_union_none_int_false(self) -> None:
        """int | None → False。"""
        assert _is_pathlib_path_annotation(int | None) is False


# ============================================================
# _endpoint_form_mutex_violation
# ============================================================


def _make_dependant(
    *,
    form_body_params: list[ModelField] | None = None,
    file_body_params: list[ModelField] | None = None,
    pure_body_params: list[ModelField] | None = None,
) -> Dependant:
    """构造 Dependant 的辅助方法。"""
    from pydantic.fields import FieldInfo

    def make_field(name: str, annotation: type, param_info: Form | Body | None) -> ModelField:
        field_info = FieldInfo(annotation=annotation)
        return ModelField(name=name, field_info=field_info, param_info=param_info)

    return Dependant(
        method="POST",
        path="/test",
        form_body_params=[make_field(f.name, f.field_info.annotation, f.param_info) for f in (form_body_params or [])],
        file_body_params=file_body_params or [],
        pure_body_params=pure_body_params or [],
    )


class TestEndpointFormMutexViolation:
    """测试 _endpoint_form_mutex_violation。"""

    def _make_field(self, name: str, annotation: type, param_info: Form | Body) -> ModelField:
        from pydantic.fields import FieldInfo

        field_info = FieldInfo(annotation=annotation)
        return ModelField(name=name, field_info=field_info, param_info=param_info)

    def test_no_violation_pure_basemodel_form(self) -> None:
        """仅有 BaseModel Form → 无冲突。"""
        d = _make_dependant(
            form_body_params=[self._make_field("data", UserCreateRequest, Form())],
        )
        assert _endpoint_form_mutex_violation(d) is None

    def test_violation_basemodel_form_mixed_with_non_basemodel_form(self) -> None:
        """BaseModel Form + 非 BaseModel Form 字段 → 冲突。"""
        d = _make_dependant(
            form_body_params=[
                self._make_field("data", UserCreateRequest, Form()),
                self._make_field("name", str, Form()),
            ],
        )
        result = _endpoint_form_mutex_violation(d)
        assert result is not None
        assert "form_body_params 中非 BaseModel Form 字段" in result

    def test_violation_basemodel_form_with_file_params(self) -> None:
        """BaseModel Form + file_body_params → 冲突。"""
        d = _make_dependant(
            form_body_params=[self._make_field("data", UserCreateRequest, Form())],
            file_body_params=[self._make_field("file", pathlib.Path, Form())],
        )
        result = _endpoint_form_mutex_violation(d)
        assert result is not None
        assert "file_body_params 字段" in result

    def test_violation_basemodel_form_with_pure_body(self) -> None:
        """BaseModel Form + pure_body_params → 冲突。"""
        d = _make_dependant(
            form_body_params=[self._make_field("data", UserCreateRequest, Form())],
            pure_body_params=[self._make_field("json", dict, Body())],
        )
        result = _endpoint_form_mutex_violation(d)
        assert result is not None
        assert "pure_body_params 字段" in result

    def test_no_violation_non_basemodel_form_only(self) -> None:
        """仅有非 BaseModel Form 字段 → 无冲突。"""
        d = _make_dependant(
            form_body_params=[
                self._make_field("name", str, Form()),
                self._make_field("age", int, Form()),
            ],
        )
        assert _endpoint_form_mutex_violation(d) is None

    def test_no_violation_empty_dependant(self) -> None:
        """空 Dependant → 无冲突。"""
        d = _make_dependant()
        assert _endpoint_form_mutex_violation(d) is None


# ============================================================
# _fill_scalar_form_field
# ============================================================


class TestFillScalarFormField:
    """测试 _fill_scalar_form_field 抛出 NotImplementedError。"""

    def test_raises_not_implemented_error(self) -> None:
        """调用 _fill_scalar_form_field 始终抛出 NotImplementedError。"""
        from pydantic.fields import FieldInfo

        from src.client import _fill_scalar_form_field

        field_info = FieldInfo(annotation=str)
        model_field = ModelField(name="test", field_info=field_info, param_info=Form())
        form_data = FormData()

        with pytest.raises(NotImplementedError, match="T6"):
            _fill_scalar_form_field(form_data, model_field, "value")
