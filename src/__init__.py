"""Stoma 接口自动化测试框架。

提供类似 FastAPI 声明式风格的接口定义和自动化测试能力。
"""

from src.routing import RouteMeta

__all__ = [
    "__version__",
    "RouteMeta",
]

__version__ = "0.1.0"
