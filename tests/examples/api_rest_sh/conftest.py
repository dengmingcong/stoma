"""examples/api_rest_sh/conftest。

为 stoma 演示 examples 提供共享 fixtures。

``stoma`` 包由 ``pyproject.toml`` 的 ``[tool.setuptools.package-dir] stoma = "src"``
映射到 ``src/``，因此 ``import stoma`` 真实可用；本 conftest 不需要任何 ``sys.modules`` patch。
生成代码 ``from stoma import ...`` 直接通过 Python 正常 import 解析。

Fixtures：
- ``_shared_playwright``：session 级，所有 e2e fixtures 共享的 Playwright 实例。
  避免多个 ``sync_playwright().start()`` 在同一 pytest session 内冲突。
- ``e2e_client_playwright`` / ``e2e_client``：session 级，无 auth headers
- ``auth_bearer_client``：session 级，Bearer token 鉴权的 Client。
- ``auth_apikey_header_client``：session 级，API Key header 鉴权的 Client。
- ``auth_basic_client``：session 级，Basic 鉴权的 Client。
- ``auth_apikey_query_client``：session 级，API Key query 鉴权的 Client。

每个 ``*_client_playwright`` fixture 创建独立的 APIRequestContext，
共享同一个 Playwright 实例。session 结束时统一 teardown（context.dispose() +
playwright.stop()）。

本文件不启动 mock server，不连 localhost，所有请求发往真实 api.rest.sh。
"""

from __future__ import annotations

import base64  # noqa: E402
from collections.abc import Generator  # noqa: E402

import pytest  # noqa: E402
from playwright.sync_api import APIRequestContext, Playwright, sync_playwright  # noqa: E402

from src.client import Client  # noqa: E402

__all__ = [
    "e2e_client",
    "e2e_client_playwright",
    "auth_bearer_client",
    "auth_apikey_header_client",
    "auth_basic_client",
    "auth_apikey_query_client",
]


@pytest.fixture(scope="session")
def _shared_playwright() -> Generator[Playwright, None, None]:
    """所有 e2e fixtures 共享的 Playwright session 实例。

    每次 sync_playwright().start() 创建独立 asyncio loop，但 pytest
    session 共享同一事件循环；多个 Playwright 实例会冲突。因此
    用单个 session fixture + 每个 client fixture 创建独立的
    APIRequestContext。
    """
    playwright_instance: Playwright = sync_playwright().start()
    try:
        yield playwright_instance
    finally:
        playwright_instance.stop()


@pytest.fixture(scope="session")
def e2e_client_playwright(
    _shared_playwright: Playwright,
) -> Generator[APIRequestContext, None, None]:
    """匿名客户端：no auth headers."""
    context: APIRequestContext = _shared_playwright.request.new_context(
        base_url="https://api.rest.sh",
    )
    try:
        yield context
    finally:
        context.dispose()


@pytest.fixture(scope="session")
def e2e_client(
    e2e_client_playwright: APIRequestContext,
) -> Generator[Client, None, None]:
    """包装 :class:`src.client.Client` 供 e2e 测试使用。"""
    client = Client(context=e2e_client_playwright)
    try:
        yield client
    finally:
        client.dispose()


@pytest.fixture(scope="session")
def auth_bearer_client_playwright(
    _shared_playwright: Playwright,
) -> Generator[APIRequestContext, None, None]:
    """带 Bearer token 的 APIRequestContext（Authorization: Bearer docs-token）。"""
    context: APIRequestContext = _shared_playwright.request.new_context(
        base_url="https://api.rest.sh",
        extra_http_headers={"Authorization": "Bearer docs-token"},
    )
    try:
        yield context
    finally:
        context.dispose()


@pytest.fixture(scope="session")
def auth_bearer_client(auth_bearer_client_playwright: APIRequestContext) -> Generator[Client, None, None]:
    """包装 :class:`src.client.Client` 供 Bearer token 鉴权 e2e 测试使用。"""
    client = Client(context=auth_bearer_client_playwright)
    try:
        yield client
    finally:
        client.dispose()


@pytest.fixture(scope="session")
def auth_apikey_header_client_playwright(
    _shared_playwright: Playwright,
) -> Generator[APIRequestContext, None, None]:
    """带 API Key header 的 APIRequestContext（X-API-Key: docs-key）。"""
    context: APIRequestContext = _shared_playwright.request.new_context(
        base_url="https://api.rest.sh",
        extra_http_headers={"X-API-Key": "docs-key"},
    )
    try:
        yield context
    finally:
        context.dispose()


@pytest.fixture(scope="session")
def auth_apikey_header_client(
    auth_apikey_header_client_playwright: APIRequestContext,
) -> Generator[Client, None, None]:
    """包装 :class:`src.client.Client` 供 API Key header 鉴权 e2e 测试使用。"""
    client = Client(context=auth_apikey_header_client_playwright)
    try:
        yield client
    finally:
        client.dispose()


@pytest.fixture(scope="session")
def auth_basic_client_playwright(
    _shared_playwright: Playwright,
) -> Generator[APIRequestContext, None, None]:
    """带 Basic 鉴权的 APIRequestContext（Authorization: Basic base64(docs:docs)）。"""
    basic_token: str = base64.b64encode(b"docs:docs").decode("ascii")
    context: APIRequestContext = _shared_playwright.request.new_context(
        base_url="https://api.rest.sh",
        extra_http_headers={"Authorization": f"Basic {basic_token}"},
    )
    try:
        yield context
    finally:
        context.dispose()


@pytest.fixture(scope="session")
def auth_basic_client(auth_basic_client_playwright: APIRequestContext) -> Generator[Client, None, None]:
    """包装 :class:`src.client.Client` 供 Basic 鉴权 e2e 测试使用。"""
    client = Client(context=auth_basic_client_playwright)
    try:
        yield client
    finally:
        client.dispose()


@pytest.fixture(scope="session")
def auth_apikey_query_client_playwright(
    _shared_playwright: Playwright,
) -> Generator[APIRequestContext, None, None]:
    """API Key query 鉴权的 base context（query 参数在 endpoint 实例上传入）。"""
    context: APIRequestContext = _shared_playwright.request.new_context(
        base_url="https://api.rest.sh",
    )
    try:
        yield context
    finally:
        context.dispose()


@pytest.fixture(scope="session")
def auth_apikey_query_client(
    auth_apikey_query_client_playwright: APIRequestContext,
) -> Generator[Client, None, None]:
    """供 API Key query 鉴权 e2e 测试使用的 Client（query 参数在 endpoint 实例上传入）。"""
    client = Client(context=auth_apikey_query_client_playwright)
    try:
        yield client
    finally:
        client.dispose()
