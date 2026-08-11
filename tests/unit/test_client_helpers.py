"""T3: client.py 5 个 form 派发辅助函数的单元测试。"""

import pathlib
from dataclasses import dataclass
from typing import Annotated, Optional, Union

import pytest
from pydantic import BaseModel
from pydantic.fields import FieldInfo
from playwright.sync_api import FormData

from src.client import (
    _fill_scalar_form_field,
)
from src.dependencies import ModelField
from src.dependencies.utils import _classify_form_field_kind, _is_scalar_or_scalar_list_annotation
from src import Form, Query, UploadFile
from src.routing import APIRouter


router = APIRouter()


class UserData(BaseModel):
    """用户数据模型。"""
    id: int
    name: str


@dataclass(frozen=True, slots=True)
class DataClassValue:
    """用于验证 dataclass 不属于标量 Form 类型。"""

    value: str


# ============================================================
# _is_scalar_or_scalar_list_annotation
# ============================================================


class TestIsScalarOrScalarListAnnotation:
    """测试标量或标量列表注解识别。"""

    @pytest.mark.parametrize(
        "annotation",
        [
            str,
            int,
            float,
            bool,
            bytes,
            list[str],
            list[int],
            Optional[str],
            str | None,
            Optional[list[str]],
            list[str] | None,
            Annotated[str, Form()],
            Annotated[list[str], Form()],
            Union[str | None, list[str] | None],
        ],
    )
    def test_scalar_annotations_true(self, annotation: type) -> None:
        """标量及其允许的包装形式 → True。"""
        assert _is_scalar_or_scalar_list_annotation(annotation) is True

    @pytest.mark.parametrize(
        "annotation",
        [
            UploadFile,
            list[UploadFile],
            Optional[UploadFile],
            pathlib.Path,
            list[pathlib.Path],
            Optional[pathlib.Path],
            BaseModel,
            dict,
            DataClassValue,
            Union[str, pathlib.Path],
        ],
    )
    def test_non_scalar_annotations_false(self, annotation: type) -> None:
        """文件、路径、复杂类型及混合并集 → False。"""
        assert _is_scalar_or_scalar_list_annotation(annotation) is False


# ============================================================
# _fill_scalar_form_field
# ============================================================


class TestFillScalarFormField:
    """测试 _fill_scalar_form_field 的四象限派发。"""

    @staticmethod
    def _fill(annotation: object, value: object) -> FormData:
        # 与 ``src.routing`` 分类阶段一致：用 ``_classify_form_field_kind`` 推断 kind 后写入 Form 实例。
        # 测试直接调 ``_fill_scalar_form_field``，跳过 routing，因此需要在这里手动设置。
        form = Form()
        kind = _classify_form_field_kind(annotation)
        if kind is not None:
            form.kind = kind
        field_info = FieldInfo(annotation=annotation)
        model_field = ModelField(name="field", field_info=field_info, param_info=form)
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
