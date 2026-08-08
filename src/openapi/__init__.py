"""OpenAPI 解析模块。

提供从 OpenAPI Specification 文件生成接口定义的功能。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.openapi.models import Endpoint

if TYPE_CHECKING:
    from src.openapi.parser import OpenAPIParser


def __getattr__(name: str) -> object:
    """延迟加载尚未就绪的子模块导出。"""
    if name == "OpenAPIParser":
        from src.openapi.parser import OpenAPIParser

        return OpenAPIParser
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


__all__ = ["Endpoint", "OpenAPIParser"]
