"""项目级 pytest fixtures。

``_shared_playwright`` 是会话级（session-scoped）的 Playwright 实例，
所有需要 Playwright 的 e2e / 集成测试都通过这一份 fixture 共享同一个
Playwright runtime + 同一个 asyncio loop。

设计原因：

- ``sync_playwright().start()`` 每次会创建独立 asyncio loop，跨 fixture
  边界的状态切换会让 Python 缓存的事件循环策略指向已关闭的 loop，
  后续调用 ``sync_playwright().start()`` 会看到假活状态而抛
  "It looks like you are using Playwright Sync API inside the asyncio loop"。
- 解决方式是让整 pytest session 共用一个 Playwright 实例 → 共用一个
  asyncio loop，没有任何 loop 切换。
- 子目录 ``tests/integration``、``tests/examples/petstore``、
  ``tests/examples/api_rest_sh`` 都不再各自定义 ``_shared_playwright``，
  pytest 自动从顶层 conftest 继承。
"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from playwright.sync_api import Playwright, sync_playwright

__all__ = ["_shared_playwright"]


@pytest.fixture(scope="session")
def _shared_playwright() -> Generator[Playwright, None, None]:
    """会话级共享的 Playwright 实例。

    整个 pytest session 内所有 e2e / 集成测试共用同一个 Playwright runtime
    与 asyncio loop，避免 ``sync_playwright().start()`` 多次启动造成的事件循环
    状态污染。session 结束时统一 ``stop()`` 释放资源。
    """
    playwright_instance: Playwright = sync_playwright().start()
    try:
        yield playwright_instance
    finally:
        playwright_instance.stop()
