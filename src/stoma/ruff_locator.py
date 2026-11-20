"""定位 ruff 可执行文件。

生成代码的 import 整理依赖 ruff。ruff 既可能作为 Python 包安装（``pip install
ruff``），也可能只存在于 PATH 上（系统包管理器、pipx 等）。本模块按可靠性
从高到低的顺序查找：

1. **ruff Python 包** —— 通过 ``ruff.__main__.find_ruff_bin()`` 拿到二进制绝对
   路径。这条路不依赖 PATH：虚拟环境里的 ruff 只有在激活后才会进入 PATH，
   而用户常用 ``uv run stoma``、docker 内直接跑、或全局安装的方式调用 CLI。
2. **PATH** —— ``shutil.which("ruff")``。覆盖 ruff 未作为 Python 包安装的场景。

两者都找不到时返回 ``None``，调用方跳过 import 整理步骤。
"""

from __future__ import annotations

import shutil
from typing import Any


def find_ruff() -> str | None:
    """查找 ruff 可执行文件的路径。

    先查 ruff Python 包（不依赖 PATH），再查 PATH。

    :return: ruff 可执行文件的绝对路径；找不到时返回 ``None``。
    """
    try:
        from ruff.__main__ import find_ruff_bin
    except ImportError:
        pass
    else:
        path: Any = find_ruff_bin()
        return str(path) if path else None

    return shutil.which("ruff")
