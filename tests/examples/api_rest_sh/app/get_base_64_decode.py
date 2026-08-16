"""Base64-url decode a value。

Generated from OpenAPI: get-base64-decode
"""

from __future__ import annotations

from .models import GetBase64DecodeResponse
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/base64/decode/{value}")
class GetBase64Decode(APIRoute[GetBase64DecodeResponse]):
    """Base64-url decode a value。
    """
    value: str
