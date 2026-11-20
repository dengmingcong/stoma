"""双语文档的语言链接一致性测试。

仓库以英文为默认语言：``README.md`` 与 ``docs/`` 下各文档的默认文件名为英文版本，
中文版本用 ``.zh.md`` 后缀并存。本测试守住两条不变式：

1. **链接不跨语言** —— 英文文档的仓库内文档链接只指向英文目标，
   中文文档的只指向中文目标（``.zh.md``）。README 顶部的语言切换器**有意**跨语言，
   单独排除。
2. **链接目标存在** —— 仓库内文档链接指向的文件必须真实存在。
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BLOB_PREFIX = "https://github.com/dengmingcong/stoma/blob/master/"

DOCS = sorted(
    [p for p in (REPO_ROOT / "docs").rglob("*.md") if "promotion" not in p.parts]
    + [REPO_ROOT / "README.md", REPO_ROOT / "README.zh.md"]
)


def _strip_language_switcher(text: str) -> str:
    """去掉 README 的语言切换器 —— 它是有意跨语言的。"""
    return re.sub(r"<!-- README-I18N:START -->.*?<!-- README-I18N:END -->", "", text, flags=re.S)


def _repo_doc_links(path: Path) -> list[str]:
    """取出该文件中指向仓库内 markdown 文档的链接。"""
    text = path.read_text(encoding="utf-8")
    text = _strip_language_switcher(text)
    raw = re.findall(r"\]\(([^)]+)\)", text) + re.findall(r'href="([^"]+)"', text)

    links: list[str] = []
    for link in raw:
        if link.startswith("#"):
            continue
        if link.startswith(BLOB_PREFIX):
            local = link[len(BLOB_PREFIX) :]
        elif link.startswith("http"):
            continue
        else:
            local = str((path.parent / link).resolve().relative_to(REPO_ROOT))
        if local.endswith(".md"):
            links.append(local)
    return links


@pytest.mark.parametrize("doc", DOCS, ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_doc_links_exist(doc: Path) -> None:
    """仓库内文档链接指向的文件必须存在。"""
    missing = [link for link in _repo_doc_links(doc) if not (REPO_ROOT / link).exists()]
    assert not missing, f"{doc.relative_to(REPO_ROOT)} 链到不存在的文件: {missing}"


@pytest.mark.parametrize("doc", DOCS, ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_doc_links_stay_in_language(doc: Path) -> None:
    """英文文档只链英文文档，中文文档只链中文文档。"""
    source_is_chinese = doc.name.endswith(".zh.md")
    wrong = [link for link in _repo_doc_links(doc) if (link.endswith(".zh.md")) is not source_is_chinese]
    assert not wrong, (
        f"{doc.relative_to(REPO_ROOT)} 的链接跨了语言（应为{'中文' if source_is_chinese else '英文'}）: {wrong}"
    )


def test_readme_has_language_switcher() -> None:
    """README 必须带居中的语言切换器，且只出现在 README 上。"""
    for name in ("README.md", "README.zh.md"):
        text = (REPO_ROOT / name).read_text(encoding="utf-8")
        assert "README-I18N:START" in text, f"{name} 缺少语言切换器"
        assert '<p align="center">' in text, f"{name} 的语言切换器未居中"

    for doc in DOCS:
        if doc.name.startswith("README"):
            continue
        text = doc.read_text(encoding="utf-8")
        assert "README-I18N" not in text, f"{doc.relative_to(REPO_ROOT)} 不应带语言切换器"
