"""仓库不应跟踪临时脚本。

开发过程中用 ``.tmp_*.py`` 之类的临时脚本做对比与校验。它们是工作材料，
不是仓库的一部分 —— ``git add -A`` 会把它们一并提交，因此用测试守住这条线。

git 不可用时跳过：某些环境下 git 是个 shell shim，跨架构的 Python 解释器
可能无法启动它（xcrun 报错）。此时不视为失败 —— 守不住等于没守住，
但也不能因为环境问题让测试变红。
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# 临时文件的命名模式
TEMP_PREFIXES = (".tmp_",)
TEMP_SUFFIXES = (".tmp", ".bak")


def _tracked_files() -> list[str] | None:
    """git 跟踪的文件列表；git 不可用时返回 None。"""
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, OSError):
        return None
    return result.stdout.splitlines()


def test_no_temp_files_tracked() -> None:
    """git 跟踪的文件里不应有临时脚本。"""
    tracked = _tracked_files()
    if tracked is None:
        pytest.skip("git 在当前环境不可用")

    offenders = []
    for path in tracked:
        name = Path(path).name
        if name.startswith(TEMP_PREFIXES) or name.endswith(TEMP_SUFFIXES):
            offenders.append(path)

    assert not offenders, f"仓库跟踪了临时文件: {offenders}"
