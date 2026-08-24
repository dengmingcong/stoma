"""tests/examples/petstore/conftest。

为 stoma 演示 examples 提供共享 fixtures，target = Swagger Petstore (https://petstore3.swagger.io)。

URL 前缀处理：
- Petstore spec 的 ``servers`` 字段声明 base path 为 ``/api/v3``。
- 生成代码通过 ``APIRouter(prefix="/api/v3")`` 在装饰期注入此前缀，
  因此每个 endpoint 的 path 已经是 ``/api/v3/...``。
- Playwright 的 ``base_url`` 设为域名根 ``https://petstore3.swagger.io``，
  ``request.fetch("/api/v3/...")`` 自动拼接完整 URL。

Fixtures：
- ``_shared_playwright``：session 级，所有 e2e fixtures 共享的 Playwright 实例。
  避免多个 ``sync_playwright().start()`` 在同一 pytest session 内冲突。
- ``e2e_client_playwright``：session 级，no auth headers，base_url 指向 petstore3.swagger.io 域名根。
- ``e2e_client``：session 级，包装 :class:`stoma.client.Client`。

每个 ``*_client_playwright`` fixture 创建独立的 APIRequestContext，
共享同一个 Playwright 实例。session 结束时统一 teardown（context.dispose() +
playwright.stop()）。

本文件不启动 mock server，所有请求发往真实 petstore3.swagger.io。
"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from playwright.sync_api import APIRequestContext, Playwright, sync_playwright

from stoma.client import Client

__all__ = [
    "e2e_client",
    "e2e_client_playwright",
]


@pytest.fixture(scope="session")
def _shared_playwright() -> Generator[Playwright, None, None]:
    """所有 e2e fixtures 共享的 Playwright session 实例。

    每次 ``sync_playwright().start()`` 创建独立 asyncio loop，但 pytest
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
    """匿名客户端：no auth headers，base_url 指向 petstore3.swagger.io 域名根。

    每个 endpoint 的 path 由生成代码的 ``APIRouter(prefix="/api/v3")`` 自动拼前缀，
    因此 ``base_url`` 不需要带 path 段。``fetch()`` 会按 RFC3986 拼接出完整 URL。
    """
    inner: APIRequestContext = _shared_playwright.request.new_context(
        base_url="https://petstore3.swagger.io",
    )
    try:
        yield inner
    finally:
        inner.dispose()


@pytest.fixture(scope="session")
def e2e_client(
    e2e_client_playwright: APIRequestContext,
) -> Generator[Client, None, None]:
    """包装 :class:`stoma.client.Client` 供 e2e 测试使用。"""
    client = Client(context=e2e_client_playwright)
    try:
        yield client
    finally:
        client.dispose()
