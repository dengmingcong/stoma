"""``src.openapi.naming`` 的单元测试。

迁移自 :mod:`tests.unit.test_cli.test_file_naming` —— 之前被混入
``test_cli/`` 包内，但实际测试的是 :mod:`src.openapi.naming` 模块（camelCase /
PascalCase / snake_case 操作 ID 到文件名 / 类名的派生规则）。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from stoma.cli import app


class TestMakeFileNaming:
    """测试生成文件的命名规则。"""

    def test_camelcase_operation_id_becomes_snake_case(self, cli_runner: Any, valid_spec: tuple[Path, Path]) -> None:
        """验证 camelCase 的 operationId 转为 snake_case 文件名。"""
        spec_file, out_dir = valid_spec

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        # listUsers → list_users.py
        assert (out_dir / "endpoints" / "list_users.py").exists()
        assert (out_dir / "endpoints" / "get_user.py").exists()
        assert (out_dir / "endpoints" / "delete_user.py").exists()

    def test_snake_case_operation_id(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证 snake_case 的 operationId 直接用作文件名。"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(
            """\
openapi: 3.1.0
info:
  title: Snake API
  version: "1.0.0"
paths:
  /items:
    get:
      operationId: list_items
      summary: 列出
      responses:
        "200":
          description: ok
""",
            encoding="utf-8",
        )
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        assert (out_dir / "endpoints" / "list_items.py").exists()

    def test_pascalcase_operation_id_becomes_snake_case(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证 PascalCase 的 operationId 转为 snake_case 文件名。"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(
            """\
openapi: 3.1.0
info:
  title: Pascal API
  version: "1.0.0"
paths:
  /items:
    get:
      operationId: ListItems
      summary: 列出
      responses:
        "200":
          description: ok
""",
            encoding="utf-8",
        )
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        assert (out_dir / "endpoints" / "list_items.py").exists()

    def test_class_name_in_file_is_pascal_case(self, cli_runner: Any, tmp_path: Path) -> None:
        """验证文件名是 snake_case 但类名是 PascalCase。"""
        spec_file = tmp_path / "spec.yaml"
        spec_file.write_text(
            """\
openapi: 3.1.0
info:
  title: Class API
  version: "1.0.0"
paths:
  /users:
    get:
      operationId: listUsers
      summary: 列出用户
      responses:
        "200":
          description: ok
""",
            encoding="utf-8",
        )
        out_dir = tmp_path / "output"

        result = cli_runner.invoke(app, [str(spec_file), "--out", str(out_dir)])

        assert result.exit_code == 0, result.output
        # 文件名是 snake_case。
        assert (out_dir / "endpoints" / "list_users.py").exists()
        # 类名是 PascalCase。
        content = (out_dir / "endpoints" / "list_users.py").read_text(encoding="utf-8")
        assert "class ListUsers" in content
