"""tests/examples/api_rest_sh/test_codegen - 验证 codegen 生成的代码结构。

本测试文件不依赖网络连接，仅对生成代码做静态文件检查和 AST 解析验证。
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

APP_DIR: Path = Path(__file__).parent / "app"

TARGET_ROUTE_FILES: list[str] = [
    "get_method.py",
    "get_anything_path.py",
    "post_method.py",
    "post_login.py",
    "post_upload.py",
    "patch_book.py",
    "delete_book.py",
    "head_method.py",
    "options_method.py",
    "get_bytes.py",
    "get_accept_image.py",
    "get_status.py",
    "get_etag.py",
]


def test_codegen_produces_all_target_files() -> None:
    """验证 models.py 和 13 个目标 route 文件均存在。"""
    models: Path = APP_DIR / "models.py"
    assert models.exists(), "models.py missing in app/"

    for route_file in TARGET_ROUTE_FILES:
        path: Path = APP_DIR / route_file
        assert path.exists(), f"{route_file} missing in app/"


def test_all_generated_files_parse_as_valid_python() -> None:
    """验证 app/ 下所有 .py 文件均可被 ast.parse() 成功解析，无语法错误。"""
    py_files: list[Path] = list(APP_DIR.glob("*.py"))
    assert py_files, "app/ 目录下未找到任何 .py 文件"

    syntax_errors: list[tuple[str, str]] = []
    for py_file in py_files:
        code: str = py_file.read_text(encoding="utf-8")
        try:
            ast.parse(code)
        except SyntaxError as e:
            syntax_errors.append((py_file.name, str(e)))

    assert not syntax_errors, (
        "以下文件存在语法错误:\n"
        + "\n".join(f"  {name}: {err}" for name, err in syntax_errors)
    )


def test_generated_files_use_stoma_import() -> None:
    """验证生成的文件中至少 71 个 .py 文件包含 ``from stoma import``。"""
    py_files: list[Path] = list(APP_DIR.glob("*.py"))
    assert py_files, "app/ 目录下未找到任何 .py 文件"

    stoma_import_pattern: re.Pattern[str] = re.compile(r"^from stoma import", re.MULTILINE)
    files_with_stoma_import: list[str] = []

    for py_file in py_files:
        code: str = py_file.read_text(encoding="utf-8")
        if stoma_import_pattern.search(code):
            files_with_stoma_import.append(py_file.name)

    count: int = len(files_with_stoma_import)
    assert count >= 71, (
        f"期望至少 71 个文件包含 'from stoma import'，实际找到 {count} 个:\n"
        + "\n".join(f"  {name}" for name in files_with_stoma_import)
    )
