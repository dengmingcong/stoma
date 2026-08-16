"""``src.client.Client._execute_request`` 与参数派发的单元测试。

合并自以下历史文件：

- :mod:`tests.unit.test_dispatcher_trace` —— TRACE 方法派发验证。
- :mod:`tests.unit.test_execute_request_headers` —— BINARY 分支 header 优先级 +
  JSON 空 body 路径。
- :mod:`tests.unit.test_param_collection` 中的 ``TestRawPayloadAndMediaType``
  dispatch 测试 —— ``_execute_request`` 对 RAW + dict/scalar body、media_type
  → Content-Type 派生、caller header 覆盖派生的优先级。

``test_execute_request_headers`` 末尾的 ``test_form_media_type_kwarg_raises_type_error``
不属于 client 派发语义、而属于 ``Form()`` 标记本身（已在
:mod:`tests.unit.test_routing` 覆盖），此处删除避免重复。
"""

from typing import Any
from unittest.mock import MagicMock

from src.client import Client
from src.dependencies.request import (
    RawPayload,
    Request,
    RequestBody,
    RequestBodyKind,
)


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
        """BINARY + 空 caller headers → ``Content-Type`` 来自 ``binary_file.mimeType``。"""
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


def test_execute_request_sends_trace_method() -> None:
    """验证 ``_execute_request`` 以 TRACE 方法调用 fetch。"""
    mock_fetch = MagicMock()
    mock_context = MagicMock(fetch=mock_fetch)
    client = Client(context=mock_context)

    client._execute_request(
        Request(
            method="TRACE",
            path="/x",
            params={},
            headers={},
            body=RequestBody(kind=RequestBodyKind.RAW, raw_data=RawPayload({}, None)),
        )
    )

    mock_fetch.assert_called_once()
    call_kwargs = mock_fetch.call_args.kwargs
    assert call_kwargs["method"] == "TRACE"


class TestExecuteRequestRawPayloadDispatch:
    """``_execute_request`` 对 RAW + ``raw_data`` 的派发语义。"""

    def test_execute_request_raw_payload_dispatch(self) -> None:
        """``_execute_request`` 对 RAW + dict body → ``data=dict``。"""
        client, fetch = _make_client()

        client._execute_request(
            Request(
                method="POST",
                path="/x",
                params={},
                headers={},
                body=RequestBody(
                    kind=RequestBodyKind.RAW,
                    raw_data=RawPayload(value={"k": 1}, media_type=None),
                ),
            )
        )
        kwargs = fetch.call_args.kwargs
        assert kwargs["data"] == {"k": 1}

    def test_execute_request_raw_payload_scalar_dispatch(self) -> None:
        """``_execute_request`` 对 RAW + scalar body → ``data=scalar``。"""
        client, fetch = _make_client()

        client._execute_request(
            Request(
                method="POST",
                path="/x",
                params={},
                headers={},
                body=RequestBody(
                    kind=RequestBodyKind.RAW,
                    raw_data=RawPayload(value=5, media_type=None),
                ),
            )
        )
        kwargs = fetch.call_args.kwargs
        assert kwargs["data"] == 5

    def test_raw_payload_media_type_sets_content_type_header(self) -> None:
        """``_execute_request``: ``raw_data.media_type`` → Content-Type header。"""
        client, fetch = _make_client()

        client._execute_request(
            Request(
                method="POST",
                path="/x",
                params={},
                headers={},
                body=RequestBody(
                    kind=RequestBodyKind.RAW,
                    raw_data=RawPayload(value=5, media_type="text/plain"),
                ),
            )
        )
        kwargs = fetch.call_args.kwargs
        assert kwargs["headers"] == {"Content-Type": "text/plain"}

    def test_raw_payload_header_overrides_media_type(self) -> None:
        """``_execute_request``: caller headers 覆盖 ``raw_data.media_type``。"""
        client, fetch = _make_client()

        client._execute_request(
            Request(
                method="POST",
                path="/x",
                params={},
                headers={"Content-Type": "application/x-custom"},
                body=RequestBody(
                    kind=RequestBodyKind.RAW,
                    raw_data=RawPayload(value=5, media_type="text/plain"),
                ),
            )
        )
        kwargs = fetch.call_args.kwargs
        assert kwargs["headers"] == {"Content-Type": "application/x-custom"}
