"""Base64-url encode a value。

Generated from OpenAPI: get-base64-encode
"""

from __future__ import annotations

from stoma import APIRoute, ResponseSpec

from ..models import ErrorModel, GetBase64EncodeResponse
from ..router import router


@router.get("/base64/encode/{value}")
class GetBase64Encode(APIRoute):
    """Base64-url encode a value。"""

    value: str

    @property
    def on_200(self) -> ResponseSpec[GetBase64EncodeResponse]:
        return ResponseSpec(
            status_code=200,
            media_type="application/json",
            expected_type=GetBase64EncodeResponse,
        )

    @property
    def on_default(self) -> ResponseSpec[ErrorModel]:
        return ResponseSpec(
            status_code=lambda c: c not in [200],
            media_type="application/problem+json",
            expected_type=ErrorModel,
        )
