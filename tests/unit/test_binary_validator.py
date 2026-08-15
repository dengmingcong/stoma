"""validate_binary_body_annotation 与 binary_file 形状的单元测试。

覆盖重命名后的抛错校验函数，以及 ``_serialize_body_params`` 在
``upload_as_multipart=False`` 模式下构造 ``FilePayload`` 的行为。
"""

from typing import Any, Optional, Union

import pytest

from dependencies.annotation import validate_binary_body_annotation
from src import UploadFile
from src.client import Client, RequestBodyKind
from src.routing import APIRoute, APIRouter


class TestValidateBinaryBodyAnnotation:
    """validate_binary_body_annotation 的行为。"""

    def test_bare_uploadfile_passes(self) -> None:
        """裸 ``UploadFile`` 通过校验。"""
        assert validate_binary_body_annotation(UploadFile, field_name="f") is None

    def test_optional_uploadfile_passes(self) -> None:
        """``UploadFile | None`` 通过校验。"""
        assert validate_binary_body_annotation(UploadFile | None, field_name="f") is None

    def test_typing_optional_uploadfile_passes(self) -> None:
        """``Optional[UploadFile]`` 通过校验。"""
        assert validate_binary_body_annotation(Optional[UploadFile], field_name="f") is None

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
            validate_binary_body_annotation(Union[UploadFile, int], field_name="x")


class TestBinaryBodySerialization:
    """``Client._serialize_body_params`` 在 ``upload_as_multipart=False`` 下产出 ``FilePayload``。"""

    def _route(self) -> Any:
        """构造最小 ``APIRoute`` + ``APIRouter`` 用于 raw-body 序列化。"""
        router = APIRouter()

        @router.post("/upload-raw", upload_as_multipart=False)
        class R(APIRoute[dict[str, Any]]):
            file: UploadFile

        return R

    def test_txt_file_yields_full_filepayload(self, tmp_path: Any) -> None:
        """``.txt`` 文件 → ``FilePayload`` 含 name / mimeType / buffer。"""
        path = tmp_path / "note.txt"
        path.write_bytes(b"hi")
        R = self._route()
        body = Client(context=None)._serialize_body_params(
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
        R = self._route()
        body = Client(context=None)._serialize_body_params(
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
        class R(APIRoute[dict[str, Any]]):
            file: UploadFile | None = None

        body = Client(context=None)._serialize_body_params(
            R(),
            R._get_dependant(method="POST", path="/upload-raw-opt", upload_as_multipart=False),
        )
        assert body.kind is RequestBodyKind.BINARY
        assert body.binary_file is None
