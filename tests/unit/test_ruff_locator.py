"""``stoma.ruff_locator.find_ruff`` 的单元测试。

ruff 的定位有两条路径：ruff Python 包（不依赖 PATH）与 PATH。本测试覆盖：

- ruff 作为 Python 包安装时能找到 —— 这是新增依赖后的主路径
- 两条路都找不到时返回 ``None`` —— 调用方据此跳过 import 整理
- 找到的路径确实是个可执行文件，且能被 subprocess 直接调用 —— CLI 就是这样用的
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from stoma.ruff_locator import find_ruff


def test_find_ruff_returns_none_when_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    """ruff 两条路都找不到时返回 None。

    用 ``sys.modules`` 里的 ``None`` 覆盖 ruff 包 —— Python 会让
    ``from ruff.__main__ import ...`` 抛 ImportError，正好是「没装」的情形。
    """
    monkeypatch.setitem(sys.modules, "ruff", None)
    monkeypatch.setitem(sys.modules, "ruff.__main__", None)
    monkeypatch.setattr("shutil.which", lambda _name: None)

    assert find_ruff() is None


def test_find_ruff_finds_installed_package() -> None:
    """ruff 作为依赖安装时能找到，且路径指向真实存在、可执行的文件。"""
    path = find_ruff()

    if path is None:
        pytest.skip("当前环境未安装 ruff")

    assert Path(path).exists(), f"find_ruff 返回的路径不存在: {path}"
    assert os.access(path, os.X_OK), f"find_ruff 返回的路径不可执行: {path}"


def test_found_ruff_is_runnable() -> None:
    """找到的 ruff 能直接用 subprocess 调用 —— CLI 就是这样用的。"""
    path = find_ruff()

    if path is None:
        pytest.skip("当前环境未安装 ruff")

    result = subprocess.run(
        [path, "--version"],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, f"ruff --version 失败: {result.stderr}"
    assert "ruff" in result.stdout.lower()
