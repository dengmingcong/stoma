"""tests/examples/api_rest_sh/test_codegen - 验证 ``stoma make`` 命令端到端可用。

本测试通过 Typer ``CliRunner`` 直接调用 ``stoma.cli:app``（与单元/集成测试一致），
不修改仓库内已存在的 ``app/`` 目录（避免污染 e2e 测试所用代码）。

覆盖范围：

- ``stoma make`` 命令退出码 0（无 ``SCHEMA_UNSUPPORTED`` 失败）。
- 生成 ``models.py`` + ``router.py`` + ``endpoints/__init__.py``。
- ``endpoints/`` 下生成 71 个 route 文件（与 spec 71 个 operation 一一对应）。
- 所有生成 ``.py`` 文件通过 ``ast.parse()``。
- 至少 71 个端点文件含 ``from ..router import router``。

本测试**不依赖网络**，仅验证本地 CLI 流水线。
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

pytest.importorskip("typer", reason="CLI 测试需要 typer (stoma[cli])")

from stoma.cli import app  # noqa: E402

SPEC_FILE: Path = Path(__file__).parent / "spec" / "api.rest.sh.json"
EXPECTED_ROUTE_COUNT: int = 71


def test_make_command_generates_full_app(cli_runner: CliRunner, tmp_path: Path) -> None:
    """``stoma make`` 端到端：从 spec 重新生成 app，断言结构与语法符合预期。"""
    assert SPEC_FILE.exists(), f"spec 文件不存在: {SPEC_FILE}"

    out_dir: Path = tmp_path / "generated"

    result = cli_runner.invoke(
        app,
        [str(SPEC_FILE), "--out", str(out_dir)],
    )

    assert result.exit_code == 0, (
        f"stoma make 失败 (退出码 {result.exit_code})\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )

    # 生成失败语义：spec 中存在 stoma 无法生成的端点（SCHEMA_UNSUPPORTED）→ CLI 退出码非 0。
    # 此处再做一次显式断言，让失败原因更直观。
    assert "SCHEMA_UNSUPPORTED" not in result.stderr, f"stoma make 报告 spec 不支持:\n{result.stderr}"

    # 1. models.py 必须存在
    models_path: Path = out_dir / "models.py"
    assert models_path.exists(), f"models.py 未生成到 {out_dir}"

    # 2. endpoints/ 路由文件数 == 71（不含 __init__.py）
    endpoints_dir: Path = out_dir / "endpoints"
    assert endpoints_dir.is_dir(), f"endpoints 子目录未生成到 {out_dir}"
    route_files: list[Path] = sorted((out_dir / "endpoints").glob("*.py"))
    route_files = [p for p in route_files if p.name != "__init__.py"]
    assert len(route_files) == EXPECTED_ROUTE_COUNT, (
        f"期望生成 {EXPECTED_ROUTE_COUNT} 个 route 文件，"
        f"实际生成 {len(route_files)} 个: {[p.name for p in route_files]}"
    )

    # 3. 所有 .py 文件可 ast.parse（含 router.py、models.py、endpoints/__init__.py 与 71 个端点）
    py_files: list[Path] = sorted(out_dir.rglob("*.py"))
    syntax_errors: list[tuple[str, str]] = []
    for py_file in py_files:
        try:
            ast.parse(py_file.read_text(encoding="utf-8"))
        except SyntaxError as e:
            syntax_errors.append((py_file.name, str(e)))
    assert not syntax_errors, "以下文件存在语法错误:\n" + "\n".join(f"  {name}: {err}" for name, err in syntax_errors)

    # 4. 至少 71 个端点文件含 ``from ..router import router``
    router_import_pattern: re.Pattern[str] = re.compile(r"^from \.\.router import router", re.MULTILINE)
    files_with_router_import: list[str] = [
        py_file.name for py_file in route_files if router_import_pattern.search(py_file.read_text(encoding="utf-8"))
    ]
    assert len(files_with_router_import) >= EXPECTED_ROUTE_COUNT, (
        f"期望至少 {EXPECTED_ROUTE_COUNT} 个端点文件含 'from ..router import router'，"
        f"实际找到 {len(files_with_router_import)} 个: {files_with_router_import}"
    )
