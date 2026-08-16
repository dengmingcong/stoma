"""examples/api_rest_sh/conftest。

为 stoma 演示 examples 提供共享 fixtures：

- ``stoma_module``：autouse，patch ``sys.modules["stoma"] = sys.modules["src"]``，
  让生成代码的 ``from stoma import ...`` 能找到实际模块。
- ``e2e_client_playwright``：session 级，启动 Playwright + 创建
  ``APIRequestContext(base_url="https://api.rest.sh")``。
- ``e2e_client``：session 级，包装成 ``src.client.Client`` 供 e2e 测试使用。

本文件不启动 mock server，不连 localhost，所有请求发往真实 api.rest.sh。
"""
from __future__ import annotations

import sys
from collections.abc import Generator

import pytest
from playwright.sync_api import APIRequestContext, Playwright, sync_playwright

from src.client import Client

__all__ = ["e2e_client", "e2e_client_playwright", "stoma_module"]


@pytest.fixture(autouse=True, scope="session")
def stoma_module() -> Generator[None, None, None]:
    """在 import 生成模块前 patch ``stoma`` 别名。

    生成代码全部使用 ``from stoma import APIRouter, APIRoute, ...``，
    但项目实际 import 路径是 ``import src``。本 fixture 提前设置别名。
    参考 :func:`tests.integration.test_cli._patch_stomo_module`。
    """
    if "src" not in sys.modules:
        import src  # noqa: F401  确保 src 已 import
    sys.modules.setdefault("stoma", sys.modules["src"])
    yield


@pytest.fixture(scope="session")
def e2e_client_playwright() -> Generator[APIRequestContext, None, None]:
    """启动 Playwright 并创建指向 api.rest.sh 的 request context。"""
    playwright: Playwright = sync_playwright().start()
    context: APIRequestContext = playwright.request.new_context(
        base_url="https://api.rest.sh",
    )
    try:
        yield context
    finally:
        context.dispose()
        playwright.stop()


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
