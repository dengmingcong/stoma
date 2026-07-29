"""集成测试的 pytest fixtures。

从 `mock_server` 模块导出 `mock_server` fixture，
让测试模块可以通过参数注入自动获取。
"""

from tests.integration.mock_server import mock_server

__all__ = ["mock_server"]
