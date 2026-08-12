"""Codegen 端到端烟测：验证 OpenAPI 8 个 HTTP method 的代码生成。

每个 fixture 验证：
- CLI 生成 route.py 成功（退出码 0）
- 生成的 route.py 包含正确的 @router.<method> 装饰器
- AST 解析验证装饰器形式正确
- Content grep 验证 @router.head/options/trace 等具名装饰器存在
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "openapi_all_methods.yaml"

HTTP_METHODS: list[tuple[str, str, str]] = [
    ("opGet", "op_get", "get"),
    ("opPost", "op_post", "post"),
    ("opPut", "op_put", "put"),
    ("opPatch", "op_patch", "patch"),
    ("opDelete", "op_delete", "delete"),
    ("opHead", "op_head", "head"),
    ("opOptions", "op_options", "options"),
    ("opTrace", "op_trace", "trace"),
]


def _extract_decorators(code: str) -> list[tuple[str, str]]:
    """从 Python 源码提取装饰器信息。

    :return: [(装饰器方法名, 装饰器参数)] 列表，如 [("router.get", '"/users"')]
    """
    tree = ast.parse(code)
    decorators: list[tuple[str, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for item in node.decorator_list:
                if isinstance(item, ast.Call):
                    func = item.func
                    if isinstance(func, ast.Attribute):
                        method = func.attr
                        if isinstance(func.value, ast.Name) and func.value.id == "router":
                            if item.args and isinstance(item.args[0], ast.Constant):
                                arg = item.args[0].value
                                decorators.append((method, arg))
    return decorators


@pytest.mark.parametrize("operation_id,snake_name,router_method", HTTP_METHODS)
def test_codegen_all_methods(
    tmp_path: Path,
    operation_id: str,
    snake_name: str,
    router_method: str,
) -> None:
    """验证 8 个 HTTP method 的 codegen 输出正确。"""
    result = subprocess.run(
        [sys.executable, "-m", "src.cli", str(FIXTURE_PATH), "--out", str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
        cwd="/Users/dengmingcong/Workspace/stoma",
    )
    assert result.returncode == 0, f"CLI 失败:\nstdout: {result.stdout}\nstderr: {result.stderr}"

    route_file = tmp_path / f"{snake_name}.py"
    assert route_file.exists(), f"生成的 {route_file} 不存在"

    route_code = route_file.read_text(encoding="utf-8")

    # Content grep: 验证具名装饰器字符串存在
    expected_path = f"/op{operation_id.removeprefix('op')}"
    expected_decorator = f'@router.{router_method}("{expected_path}")'
    assert expected_decorator in route_code, f"生成的 route.py 缺少装饰器 {expected_decorator}\n实际内容:\n{route_code}"

    # AST 解析: 验证装饰器形式正确
    decorators = _extract_decorators(route_code)
    matching = [(m, a) for m, a in decorators if m == router_method and a == expected_path]
    assert len(matching) == 1, (
        f'AST 未找到装饰器 @router.{router_method}("{expected_path}")\n'
        f"AST 解析到的装饰器: {decorators}\n"
        f"文件内容:\n{route_code}"
    )

    # 验证 import 语句包含 stoma
    assert "from stoma import APIRouter, APIRoute" in route_code, (
        f"生成的 route.py 缺少 'from stoma import APIRouter, APIRoute'\n实际内容:\n{route_code}"
    )
