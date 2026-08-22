"""``src.dependencies.annotation`` 的单元测试。

合并自以下历史文件：

- :mod:`tests.unit.test_binary_validator` —— ``validate_binary_body_annotation`` 抛错 +
  ``_serialize_body_params`` 在 ``upload_as_multipart=False`` 下产出 ``FilePayload``。
- :mod:`tests.unit.test_param_recognition` 中的 ``TestComplexTypeHelpers`` —— 复杂类型
  判定（``field_annotation_is_complex``）覆盖 BaseModel / Sequence / Mapping /
  dataclass / dataclass 字段 / Union 等。

旧文件 ``from dependencies.annotation import ...``（无 ``src.`` 前缀）依赖
namespace package 巧合解析，统一改为 ``from src.dependencies.annotation import ...``。
"""

from dataclasses import dataclass
from typing import Any, Optional, Union

import pytest
from pydantic import BaseModel

from stoma import JSONResponseSpec, UploadFile
from stoma.dependencies.annotation import (
    field_annotation_is_complex,
    validate_binary_body_annotation,
)
from stoma.dependencies.request import RequestBodyKind, _serialize_body_params
from stoma.routing import APIRoute, APIRouter


class TestValidateBinaryBodyAnnotation:
    """``validate_binary_body_annotation`` 的行为。"""

    def test_bare_uploadfile_passes(self) -> None:
        """裸 ``UploadFile`` 通过校验。"""
        assert validate_binary_body_annotation(UploadFile, field_name="f") is None

    def test_optional_uploadfile_passes(self) -> None:
        """``UploadFile | None`` 通过校验。"""
        assert validate_binary_body_annotation(UploadFile | None, field_name="f") is None

    def test_typing_optional_uploadfile_passes(self) -> None:
        """``Optional[UploadFile]`` 通过校验。"""
        assert validate_binary_body_annotation(Optional[UploadFile], field_name="f") is None  # noqa: UP045

    def test_list_uploadfile_raises_with_substring_and_field_name(self) -> None:
        """``list[UploadFile]`` 抛 ``ValueError``，消息含 ``不能是 list/Form 包装`` 和字段名。"""
        with pytest.raises(ValueError) as exc:
            validate_binary_body_annotation(list[UploadFile], field_name="files")
        msg = str(exc.value)
        assert "不能是 list/Form 包装" in msg
        assert "files" in msg

    def test_unrelated_type_raises(self) -> None:
        """非 ``UploadFile`` 类型抛 ``ValueError``。"""
        with pytest.raises(ValueError) as exc:
            validate_binary_body_annotation(str, field_name="x")
        assert "x" in str(exc.value)

    def test_union_with_other_type_raises(self) -> None:
        """``Union[UploadFile, int]`` 抛 ``ValueError``。"""
        with pytest.raises(ValueError):
            validate_binary_body_annotation(Union[UploadFile, int], field_name="x")  # noqa: UP007


class TestBinaryBodySerialization:
    """``_serialize_body_params`` 在 ``upload_as_multipart=False`` 下产出 ``FilePayload``。"""

    def _route(self) -> Any:
        """构造最小 ``APIRoute`` + ``APIRouter`` 用于 raw-body 序列化。"""
        router = APIRouter()

        @router.post("/upload-raw", upload_as_multipart=False)
        class R(APIRoute):
            file: UploadFile

            @property
            def on_201(self) -> JSONResponseSpec[dict[str, Any]]:
                return JSONResponseSpec(status_code=201, media_type="application/json", model=dict[str, Any])

        return R

    def test_txt_file_yields_full_filepayload(self, tmp_path: Any) -> None:
        """``.txt`` 文件 → ``FilePayload`` 含 name / mimeType / buffer。"""
        path = tmp_path / "note.txt"
        path.write_bytes(b"hi")
        R = self._route()  # noqa: N806
        body = _serialize_body_params(
            R(file=UploadFile(path=path)),
            R._get_dependant(method="POST", path="/upload-raw", upload_as_multipart=False),
        )
        assert body.kind is RequestBodyKind.BINARY
        assert body.binary_file == {
            "name": "note.txt",
            "mimeType": "text/plain",
            "buffer": b"hi",
        }

    def test_unknown_extension_falls_back_to_octet_stream(self, tmp_path: Any) -> None:
        """``mimetypes.guess_type`` 返回 None 时回退到 ``application/octet-stream``。"""
        path = tmp_path / "data.unknownext"
        path.write_bytes(b"raw bytes")
        R = self._route()  # noqa: N806
        body = _serialize_body_params(
            R(file=UploadFile(path=path)),
            R._get_dependant(method="POST", path="/upload-raw", upload_as_multipart=False),
        )
        assert body.kind is RequestBodyKind.BINARY
        assert body.binary_file is not None
        assert body.binary_file["mimeType"] == "application/octet-stream"
        assert body.binary_file["buffer"] == b"raw bytes"

    def test_optional_none_yields_binary_file_none(self) -> None:
        """``UploadFile | None = None`` + 不传 → ``binary_file`` 为 None。"""
        router = APIRouter()

        @router.post("/upload-raw-opt", upload_as_multipart=False)
        class R(APIRoute):
            file: UploadFile | None = None

            @property
            def on_201(self) -> JSONResponseSpec[dict[str, Any]]:
                return JSONResponseSpec(status_code=201, media_type="application/json", model=dict[str, Any])

        body = _serialize_body_params(
            R(),
            R._get_dependant(method="POST", path="/upload-raw-opt", upload_as_multipart=False),
        )
        assert body.kind is RequestBodyKind.BINARY
        assert body.binary_file is None


class TestComplexTypeHelpers:
    """复杂类型判定辅助函数 ``field_annotation_is_complex``。"""

    def test_is_complex_base_model(self) -> None:
        """测试 BaseModel 子类被识别为复杂类型。"""

        class MyModel(BaseModel):
            field: str

        assert field_annotation_is_complex(MyModel) is True
        assert field_annotation_is_complex(MyModel | None) is True

    def test_is_complex_sequence(self) -> None:
        """测试序列类型被识别为复杂类型。"""
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
        assert field_annotation_is_complex(int) is False
        assert field_annotation_is_complex(str) is False
        assert field_annotation_is_complex(bool) is False
        assert field_annotation_is_complex(float) is False
        assert field_annotation_is_complex(int | str) is False  # Union of scalars

    def test_is_complex_union_with_base_model(self) -> None:
        """测试 ``BaseModel | None`` 被识别为复杂类型。"""

        # 复用 :mod:`tests.unit.test_routing` 的 ``UserData`` 不可行（跨文件），
        # 因此这里本地定义一个最小 ``BaseModel`` 子类。
        class LocalUserData(BaseModel):
            id: int
            name: str

        assert field_annotation_is_complex(LocalUserData | None) is True
        assert field_annotation_is_complex(int | LocalUserData) is True  # One is complex
