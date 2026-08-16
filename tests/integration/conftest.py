"""集成测试的 pytest fixtures。

从 :mod:`mock_server` 模块导出 ``mock_server`` fixture，
让测试模块可以通过参数注入自动获取。

同时新增 :func:`cli_runner` fixture，供 :mod:`tests.integration.test_cli`
等直接调用 ``src.cli:app`` 的端到端用例使用。
"""

import pytest
from typer.testing import CliRunner

from tests.integration.mock_server import mock_server

__all__ = ["cli_runner", "mock_server"]


@pytest.fixture
def cli_runner() -> CliRunner:
    """Typer ``CliRunner`` 实例，供 CLI 端到端测试使用。"""
    return CliRunner()
