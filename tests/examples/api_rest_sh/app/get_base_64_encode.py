"""Base64-url encode a value。

Generated from OpenAPI: get-base64-encode
"""

from __future__ import annotations

from .models import GetBase64EncodeResponse
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/base64/encode/{value}")
class GetBase64Encode(APIRoute[GetBase64EncodeResponse]):
    """Base64-url encode a value。
    """
    value: str
