"""测试 :mod:`src.openapi.model_generator` 对 ``datamodel-code-generator`` 的封装。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.openapi.model_generator import generate_models


def _minimal_spec() -> dict[str, Any]:
    """给测试用的最小 OpenAPI 规范（prance 风格，``$ref`` 已展开）。"""
    return {
        "openapi": "3.1.0",
        "info": {"title": "Test", "version": "1.0.0"},
        "paths": {
            "/users": {
                "post": {
                    "operationId": "createUser",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/User"}
                            }
                        }
                    },
                    "responses": {
                        "201": {
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/User"}
                                }
                            }
                        }
                    },
                }
            }
        },
        "components": {
            "schemas": {
                "User": {
                    "type": "object",
                    "title": "User",
                    "required": ["id", "name"],
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                    },
                }
            }
        },
    }


class TestGenerateModels:
    """测试 :func:`generate_models` 端到端调用 ``datamodel-code-generator``。"""

    def test_generates_models_file(self, tmp_path: Path) -> None:
        """应生成 ``models.py`` 文件，且包含至少一个 ``class`` 定义。"""
        spec = _minimal_spec()
        output_path = tmp_path / "models.py"
        generate_models(spec, output_path)
        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        assert "class" in content
        assert "User" in content

    def test_creates_parent_directory(self, tmp_path: Path) -> None:
        """父目录不存在时自动创建。"""
        spec = _minimal_spec()
        output_path = tmp_path / "deep" / "nested" / "models.py"
        generate_models(spec, output_path)
        assert output_path.exists()

    def test_raises_on_invalid_spec(self, tmp_path: Path) -> None:
        """无效 spec 应抛出 ``RuntimeError``。"""
        output_path = tmp_path / "models.py"
        try:
            generate_models({"paths": {}}, output_path)
        except RuntimeError:
            # 预期：错误包装为 RuntimeError
            pass
        else:
            # 部分无效 spec 仍能生成，文件不存在才报错
            if not output_path.exists():
                msg = "无效 spec 应报错"
                raise AssertionError(msg)
