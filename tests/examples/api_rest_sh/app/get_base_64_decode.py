"""Base64-url decode a value。

Generated from OpenAPI: get-base64-decode
"""

from __future__ import annotations

from stoma import APIRoute, APIRouter

from .models import ErrorModel, GetBase64DecodeResponse

router = APIRouter()


@router.get("/base64/decode/{value}")
class GetBase64Decode(APIRoute[GetBase64DecodeResponse | ErrorModel]):
    """Base64-url decode a value。"""

    value: str
