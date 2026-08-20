"""tests/examples/petstore/conftest。

为 stoma 演示 examples 提供共享 fixtures，target = Swagger Petstore (https://petstore3.swagger.io/api/v3)。

URL 前缀处理：
- Petstore spec 的 ``servers`` 字段声明 base path 为 ``/api/v3``。
- 生成代码的 route 路径不带此前缀（如 ``/store/inventory``）。
- Playwright 的 ``base_url`` 拼接遵循 RFC3986：以 ``/`` 开头的路径会**替换** base URL 路径，
  因此 ``base_url='https://petstore3.swagger.io/api/v3'`` + ``/store/inventory`` 会得到
  ``https://petstore3.swagger.io/store/inventory``（丢失 ``/api/v3``）。
- 解决方案：用 ``Petstore3Context`` 装饰器包一层 APIRequestContext，
  在调用 ``fetch()`` 时主动给 path 加上 ``/api/v3`` 前缀。
- 这样既不需要修改 ``src/``，也不需要修改生成代码。

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

from collections.abc import Generator  # noqa: E402

import pytest  # noqa: E402
from playwright.sync_api import APIRequestContext, APIResponse, Playwright, sync_playwright  # noqa: E402

from stoma.client import Client  # noqa: E402

__all__ = [
    "Petstore3Context",
    "e2e_client",
    "e2e_client_playwright",
]


class Petstore3Context:
    """为 ``base_url`` 域名的路径前缀 ``/api/v3`` 补齐。

    Playwright 的 ``APIRequestContext.fetch()`` 遵循 RFC3986 URL 拼接：以 ``/``
    开头的 path 会替换 base URL 的整个 path 段。Petstore 声明 base path 为
    ``/api/v3``，但生成的 route 路径不带此前缀，因此需要在 fetch 之前主动
    给 path 加上 ``/api/v3`` 前缀。

    本类用鸭子类型实现 ``APIRequestContext`` 的最小子集：``fetch`` 与 ``dispose``。
    """

    BASE_PATH: str = "/api/v3"

    def __init__(self, inner: APIRequestContext) -> None:
        self._inner = inner

    def fetch(self, path: str, **kwargs: object) -> APIResponse:
        """转发 fetch 调用并给 path 补上 ``/api/v3`` 前缀。"""
        if path.startswith("/"):
            full_path = self.BASE_PATH + path
        else:
            full_path = self.BASE_PATH + "/" + path
        return self._inner.fetch(full_path, **kwargs)

    def dispose(self) -> None:
        """释放底层 Playwright context。"""
        self._inner.dispose()


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

    返回 :class:`Petstore3Context`（包了一层 APIRequestContext），用于补齐
    ``/api/v3`` 路径前缀。stoma 的 ``Client`` 只调用 ``fetch`` 与 ``dispose``，
    鸭子类型即可。
    """
    inner: APIRequestContext = _shared_playwright.request.new_context(
        base_url="https://petstore3.swagger.io",
    )
    wrapper = Petstore3Context(inner)
    try:
        yield wrapper
    finally:
        wrapper.dispose()


@pytest.fixture(scope="session")
def e2e_client(
    e2e_client_playwright: APIRequestContext,
) -> Generator[Client, None, None]:
    """包装 :class:`stoma.client.Client` 供 e2e 测试使用。

    :class:`Petstore3Context` 的 ``fetch`` 会自动补齐 ``/api/v3`` 前缀，
    因此 ``Client.send`` 无需任何额外处理。
    """
    client = Client(context=e2e_client_playwright)
    try:
        yield client
    finally:
        client.dispose()
