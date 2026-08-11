"""T3: client.py form 派发逻辑的单元测试。

``_fill_scalar_form_field`` 现在直接从 ``model_field.field_info.annotation`` 读取类型
（由 Pydantic 解开 ``Annotated``），不再依赖 ``Form.kind`` 运行时缓存。
"""

import pathlib
from typing import Optional

import pytest
from pydantic import BaseModel
from pydantic.fields import FieldInfo
from playwright.sync_api import FormData

from src.client import _fill_scalar_form_field
from src.dependencies import ModelField
from src import Form


class UserData(BaseModel):
    """用户数据模型。"""
    id: int
    name: str


# ============================================================
# _fill_scalar_form_field
# ============================================================


class TestFillScalarFormField:
    """测试 ``_fill_scalar_form_field`` 基于 ``field_info.annotation`` 的派发。"""

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
