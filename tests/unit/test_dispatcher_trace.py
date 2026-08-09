"""T021c: 验证 Client._execute_request 支持 TRACE 方法。

验证 Client._execute_request 通过 Playwright fetch 发送任意 HTTP 方法，
包括 TRACE。TRACE 不做 e2e 测试（不走真实 Playwright 通道），
只做 dispatcher 单测：用 MagicMock 模拟 _context.fetch。
"""

from unittest.mock import MagicMock

from src.client import Client


def test_execute_request_sends_trace_method() -> None:
    """验证 _execute_request 以 TRACE 方法调用 fetch。"""
    mock_fetch = MagicMock()
    mock_context = MagicMock(fetch=mock_fetch)

    client = Client(context=mock_context)

    client._execute_request("TRACE", "/x", {}, {}, None)

    mock_fetch.assert_called_once()
    call_kwargs = mock_fetch.call_args.kwargs
    assert call_kwargs["method"] == "TRACE"
