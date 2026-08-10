"""Stoma 接口自动化测试框架。

提供类似 FastAPI 声明式风格的接口定义和自动化测试能力。
"""

from src.client import Client
from src.params import Body, Form, Header, UploadFile
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
    "Response",
    "UploadFile",
]

__version__ = "0.1.0"
