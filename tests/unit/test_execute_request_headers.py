"""Client._execute_request dispatch 与 header 优先级单元测试。

覆盖 BINARY 分支的默认 / override / merge / 缺省四种 header 路径，
以及 JSON 空 body 路径。
"""

from typing import Any
from unittest.mock import MagicMock

import pytest

from src import Form
from src.client import Client
from src.dependencies.request import Request, RequestBody, RequestBodyKind


def _make_client() -> tuple[Client, MagicMock]:
    """构造带 MagicMock fetch 的 Client。"""
    mock_fetch = MagicMock()
    mock_context = MagicMock(fetch=mock_fetch)
    return Client(context=mock_context), mock_fetch


class TestExecuteRequestBinaryHeaders:
    """BINARY + binary_file + caller headers 派发路径。"""

    BINARY_PAYLOAD: dict[str, Any] = {
        "name": "a.txt",
        "mimeType": "text/plain",
        "buffer": b"x",
    }

    def test_binary_default_headers_applied(self) -> None:
        """BINARY + 空 caller headers → ``Content-Type`` 来自 binary_file.mimeType。"""
        client, fetch = _make_client()
        client._execute_request(
            Request(
                method="POST",
                path="/x",
                params={},
                headers={},
                body=RequestBody(kind=RequestBodyKind.BINARY, binary_file=self.BINARY_PAYLOAD),
            )
        )
        kwargs = fetch.call_args.kwargs
        assert kwargs["data"] == b"x"
        assert kwargs["headers"] == {"Content-Type": "text/plain"}

    def test_binary_caller_content_type_wins(self) -> None:
        """BINARY + caller ``Content-Type`` 覆盖自动 mime。"""
        client, fetch = _make_client()
        client._execute_request(
            Request(
                method="POST",
                path="/x",
                params={},
                headers={"Content-Type": "application/x-custom"},
                body=RequestBody(kind=RequestBodyKind.BINARY, binary_file=self.BINARY_PAYLOAD),
            )
        )
        kwargs = fetch.call_args.kwargs
        assert kwargs["headers"] == {"Content-Type": "application/x-custom"}

    def test_binary_non_colliding_caller_header_merged(self) -> None:
        """BINARY + caller 非冲突 header → 两个都存在（derived + caller）。"""
        client, fetch = _make_client()
        client._execute_request(
            Request(
                method="POST",
                path="/x",
                params={},
                headers={"X-Trace": "1"},
                body=RequestBody(kind=RequestBodyKind.BINARY, binary_file=self.BINARY_PAYLOAD),
            )
        )
        kwargs = fetch.call_args.kwargs
        assert kwargs["headers"] == {"Content-Type": "text/plain", "X-Trace": "1"}

    def test_binary_file_none_sends_no_data_and_no_derived_content_type(self) -> None:
        """BINARY + ``binary_file=None`` → 不发 data，不派生 Content-Type。"""
        client, fetch = _make_client()
        client._execute_request(
            Request(
                method="POST",
                path="/x",
                params={},
                headers={},
                body=RequestBody(kind=RequestBodyKind.BINARY, binary_file=None),
            )
        )
        kwargs = fetch.call_args.kwargs
        assert "data" not in kwargs
        assert kwargs.get("headers") in (None, {})


class TestExecuteRequestJsonEmpty:
    """JSON 空 body 路径。"""

    def test_json_none_body_no_data_no_headers(self) -> None:
        """RAW + ``raw_data=None`` + 空 caller headers → ``data=None``, headers 缺失或空。"""
        client, fetch = _make_client()
        client._execute_request(
            Request(
                method="POST",
                path="/x",
                params={},
                headers={},
                body=RequestBody(kind=RequestBodyKind.RAW, raw_data=None),
            )
        )
        kwargs = fetch.call_args.kwargs
        assert kwargs["data"] is None
        assert kwargs.get("headers") in (None, {})


def test_form_media_type_kwarg_raises_type_error() -> None:
    """Form(media_type=...) 抛 TypeError（不接受此参数）。"""
    with pytest.raises(TypeError):
        Form(media_type="text/plain")
