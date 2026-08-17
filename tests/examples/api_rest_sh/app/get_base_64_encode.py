"""Base64-url encode a value。

Generated from OpenAPI: get-base64-encode
"""

from __future__ import annotations

from stoma import APIRoute, APIRouter

from .models import ErrorModel, GetBase64EncodeResponse

router = APIRouter()


@router.get("/base64/encode/{value}")
class GetBase64Encode(APIRoute[GetBase64EncodeResponse | ErrorModel]):
    """Base64-url encode a value。"""

    value: str
