"""T3: client.py 5 个 form 派发辅助函数的单元测试。"""

import pathlib
from typing import Annotated, Optional

import pytest
from pydantic import BaseModel
from pydantic.fields import FieldInfo
from playwright.sync_api import FormData

from src.client import (
    _classify_field_kind,
    _fill_scalar_form_field,
    _is_pathlib_path_annotation,
)
from src.dependencies import ModelField
from src.params import Form, Query
from src.routing import APIRouter


router = APIRouter()


class UserData(BaseModel):
    """用户数据模型。"""
    id: int
    name: str


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
# _fill_scalar_form_field
# ============================================================


class TestFillScalarFormField:
    """测试 _fill_scalar_form_field 的四象限派发。"""

    @staticmethod
    def _fill(annotation: object, value: object) -> FormData:
        field_info = FieldInfo(annotation=annotation)
        model_field = ModelField(name="field", field_info=field_info, param_info=Form())
        form_data = FormData()
        _fill_scalar_form_field(form_data, model_field, value)
        return form_data

    def test_scalar_str_set(self) -> None:
        """str 标量 → form_data.set 原值。"""
        assert self._fill(str, "alice")._fields == [("field", "alice")]

    def test_scalar_int_set(self) -> None:
        """int 标量原值传递，不转 str。"""
        assert self._fill(int, 42)._fields == [("field", 42)]

    def test_scalar_bool_set(self) -> None:
        """bool 标量原值传递。"""
        assert self._fill(bool, True)._fields == [("field", True)]

    def test_none_skipped(self) -> None:
        """None 值跳过，不产生任何 part。"""
        assert self._fill(Optional[str], None)._fields == []

    def test_scalar_bytes_raises(self) -> None:
        """bytes 不在 Playwright FormDataValue，抛 ValueError。"""
        with pytest.raises(ValueError, match="收到 bytes 类型"):
            self._fill(bytes, b"\x00")

    def test_scalar_dict_raises(self) -> None:
        """dict 不再自动 JSON 序列化，抛 ValueError。"""
        with pytest.raises(ValueError, match="不再自动 JSON 序列化"):
            self._fill(dict, {})

    def test_scalar_basemodel_raises(self) -> None:
        """BaseModel 实例抛 ValueError（form_body_params 已过滤，此处兜底）。"""
        with pytest.raises(ValueError, match="嵌套 BaseModel Form"):
            self._fill(UserData, UserData(id=1, name="alice"))

    def test_list_text_appends_each(self) -> None:
        """list[str] 每个元素 append 一次同名 part。"""
        assert self._fill(list[str], ["a", "b"])._fields == [("field", "a"), ("field", "b")]

    def test_list_text_skips_none_element(self) -> None:
        """list 中的 None 元素跳过，其余照常 append。"""
        assert self._fill(list[str], ["a", None, "b"])._fields == [("field", "a"), ("field", "b")]

    def test_empty_list_skipped(self) -> None:
        """空 list 不产生任何 part。"""
        assert self._fill(list[str], [])._fields == []

    def test_list_non_scalar_element_raises(self) -> None:
        """list 元素为 dict → ValueError。"""
        with pytest.raises(ValueError, match="元素收到 dict"):
            self._fill(list[str], [{"k": "v"}])

    def test_list_annotation_with_non_list_value_raises(self) -> None:
        """注解为 list 但值不是 list → ValueError。"""
        with pytest.raises(ValueError, match="注解为 list，但收到 str"):
            self._fill(list[str], "a")

    def test_list_path_appends_path_objects(self) -> None:
        """list[pathlib.Path] append 的是 Path 对象本身，不是 str。"""
        paths = [pathlib.Path("/tmp/a.txt"), pathlib.Path("/tmp/b.txt")]
        assert self._fill(list[pathlib.Path], paths)._fields == [
            ("field", paths[0]),
            ("field", paths[1]),
        ]

    def test_list_path_non_path_element_raises(self) -> None:
        """list[pathlib.Path] 元素不是 Path → ValueError。"""
        with pytest.raises(ValueError, match="元素期望 pathlib.Path，收到 str"):
            self._fill(list[pathlib.Path], ["/tmp/a.txt"])

    def test_scalar_path_annotation_raises(self) -> None:
        """标量 pathlib.Path 应由 routing 落到 file_body_params，进入本函数即报错。"""
        with pytest.raises(ValueError, match="不应进入标量派发"):
            self._fill(pathlib.Path, pathlib.Path("/tmp/a.txt"))
