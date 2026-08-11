"""Stoma 接口自动化测试框架。

提供类似 FastAPI 声明式风格的接口定义和自动化测试能力。
"""

# 顺序很重要：``UploadFile`` 必须先于 ``client`` / ``routing`` 导入。
# ``src.client`` / ``src.dependencies.utils`` 会从 ``src`` 命名空间读 ``UploadFile``，
# 而它们又是 ``src/__init__.py`` 后续 import 的对象，因此 ``UploadFile`` 必须先注入。
from src.params import UploadFile
from src.param_functions import Body, Form, Header, Path, Query
from src.client import Client
from src.response import Response
from src.routing import APIRoute, APIRouter

__all__ = [
    "__version__",
    "APIRoute",
    "APIRouter",
    "Body",
    "Client",
    "Form",
    "Header",
    "Path",
    "Query",
    "Response",
    "UploadFile",
]

__version__ = "0.1.0"
