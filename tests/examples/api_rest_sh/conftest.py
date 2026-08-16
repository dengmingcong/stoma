"""examples/api_rest_sh/conftest。

为 stoma 演示 examples 提供共享 fixtures。

模块级别 patch：
``stoma`` 别名在 conftest.py import 时即设置（不在 fixture 内），
因为生成代码在 module import time 执行 ``from stoma import ...``，
autouse fixture 来得及。pytest import 顺序保证 conftest.py 先于 test_*.py import。

Fixtures：
- ``e2e_client_playwright`` / ``e2e_client``：session 级，无 auth headers
- ``auth_bearer_client``：session 级，Bearer token 鉴权的 Client。
- ``auth_apikey_header_client``：session 级，API Key header 鉴权的 Client。
- ``auth_basic_client``：session 级，Basic 鉴权的 Client。
- ``auth_apikey_query_client``：session 级，API Key query 鉴权的 Client。

本文件不启动 mock server，不连 localhost，所有请求发往真实 api.rest.sh。
"""

from __future__ import annotations

import sys

import src as _src_module  # noqa: F401

sys.modules["stoma"] = _src_module

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


@pytest.fixture(scope="session")
def auth_bearer_client_playwright() -> Generator[APIRequestContext, None, None]:
    """带 Bearer token 的 APIRequestContext（Authorization: Bearer docs-token）。"""
    playwright: Playwright = sync_playwright().start()
    context: APIRequestContext = playwright.request.new_context(
        base_url="https://api.rest.sh",
        extra_http_headers={"Authorization": "Bearer docs-token"},
    )
    try:
        yield context
    finally:
        context.dispose()
        playwright.stop()


@pytest.fixture(scope="session")
def auth_bearer_client(auth_bearer_client_playwright: APIRequestContext) -> Generator[Client, None, None]:
    """包装 :class:`src.client.Client` 供 Bearer token 鉴权 e2e 测试使用。"""
    client = Client(context=auth_bearer_client_playwright)
    try:
        yield client
    finally:
        client.dispose()


@pytest.fixture(scope="session")
def auth_apikey_header_client_playwright() -> Generator[APIRequestContext, None, None]:
    """带 API Key header 的 APIRequestContext（X-API-Key: docs-key）。"""
    playwright: Playwright = sync_playwright().start()
    context: APIRequestContext = playwright.request.new_context(
        base_url="https://api.rest.sh",
        extra_http_headers={"X-API-Key": "docs-key"},
    )
    try:
        yield context
    finally:
        context.dispose()
        playwright.stop()


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
def auth_basic_client_playwright() -> Generator[APIRequestContext, None, None]:
    """带 Basic 鉴权的 APIRequestContext（Authorization: Basic base64(docs:docs)）。"""
    basic_token: str = base64.b64encode(b"docs:docs").decode("ascii")
    playwright: Playwright = sync_playwright().start()
    context: APIRequestContext = playwright.request.new_context(
        base_url="https://api.rest.sh",
        extra_http_headers={"Authorization": f"Basic {basic_token}"},
    )
    try:
        yield context
    finally:
        context.dispose()
        playwright.stop()


@pytest.fixture(scope="session")
def auth_basic_client(auth_basic_client_playwright: APIRequestContext) -> Generator[Client, None, None]:
    """包装 :class:`src.client.Client` 供 Basic 鉴权 e2e 测试使用。"""
    client = Client(context=auth_basic_client_playwright)
    try:
        yield client
    finally:
        client.dispose()


@pytest.fixture(scope="session")
def auth_apikey_query_client() -> Generator[Client, None, None]:
    """供 API Key query 鉴权 e2e 测试使用的 Client（query 参数在 endpoint 实例上传入）。"""
    playwright: Playwright = sync_playwright().start()
    context: APIRequestContext = playwright.request.new_context(base_url="https://api.rest.sh")
    client = Client(context=context)
    try:
        yield client
    finally:
        client.dispose()
        context.dispose()
        playwright.stop()
