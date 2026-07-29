"""Mock Server fixture：在后台线程运行 FastAPI app。

提供 `mock_server` fixture 给集成测试使用。
"""

import socket
import threading
import time
from collections.abc import Generator

import pytest
import uvicorn
from fastapi import FastAPI


def _find_free_port() -> int:
    """找一个空闲端口。"""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class _ServerThread:
    """后台运行的 uvicorn server。"""

    def __init__(self, app: FastAPI) -> None:
        self.app = app
        self.port = _find_free_port()
        self.config = uvicorn.Config(
            app,
            host="127.0.0.1",
            port=self.port,
            log_level="warning",
            access_log=False,
        )
        self.server = uvicorn.Server(self.config)
        self._thread = threading.Thread(target=self.server.run, daemon=True)

    def start(self) -> None:
        """启动 server（阻塞直到就绪）。"""
        self._thread.start()
        # 等待 server 启动（最长 5 秒）
        for _ in range(50):
            if self.server.started:
                return
            time.sleep(0.1)
        raise RuntimeError("Mock server failed to start")

    def stop(self) -> None:
        """优雅停止 server。"""
        self.server.should_exit = True
        self._thread.join(timeout=5)

    @property
    def base_url(self) -> str:
        """获取 server 的 base URL。"""
        return f"http://127.0.0.1:{self.port}"


@pytest.fixture(scope="module")
def mock_server() -> Generator[_ServerThread, None, None]:
    """模块级 fixture：启动 mock server。"""
    from tests.integration.mock_app import app

    server = _ServerThread(app)
    server.start()
    try:
        yield server
    finally:
        server.stop()
