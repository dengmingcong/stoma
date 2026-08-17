"""Stoma 接口自动化测试框架。

提供类似 FastAPI 声明式风格的接口定义和自动化测试能力。
"""

from stoma.client import Client
from stoma.dependencies.response import Response
from stoma.param_functions import Body, Form, Header, Path, Query
from stoma.params import UploadFile
from stoma.routing import APIRoute, APIRouter

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
