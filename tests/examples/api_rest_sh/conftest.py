"""examples/api_rest_sh/conftest。

为 stoma 演示 examples 提供共享 fixtures。

``stoma`` 包位于标准 ``src/stoma/`` 布局（setuptools 推荐），``import stoma`` 解析到 ``src/stoma/__init__.py``。
生成代码 ``from stoma import ...`` 直接通过 Python 正常 import 解析。

Fixtures：
- ``cli_runner``：Typer ``CliRunner`` 实例，供 ``test_codegen.py`` 调用 ``stoma make`` 命令使用。
- ``_shared_playwright``：来自顶层 ``tests/conftest.py``，session 级共享。
- ``e2e_client_playwright`` / ``e2e_client``：session 级，无 auth headers

每个 ``*_client_playwright`` fixture 创建独立的 APIRequestContext，
共享同一个 Playwright 实例。session 结束时统一 teardown（context.dispose()）。

本文件不启动 mock server，不连 localhost，所有请求发往真实 api.rest.sh。
"""

from __future__ import annotations

from collections.abc import Generator  # noqa: E402

import pytest  # noqa: E402
from playwright.sync_api import APIRequestContext, Playwright  # noqa: E402
from typer.testing import CliRunner  # noqa: E402

from stoma.client import Client  # noqa: E402

__all__ = [
    "cli_runner",
    "e2e_client",
    "e2e_client_playwright",
]


@pytest.fixture
def cli_runner() -> CliRunner:
    """Typer ``CliRunner`` 实例，供 CLI 端到端测试使用。"""
    return CliRunner()


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
    """包装 :class:`stoma.client.Client` 供 e2e 测试使用。"""
    client = Client(context=e2e_client_playwright)
    try:
        yield client
    finally:
        client.dispose()
