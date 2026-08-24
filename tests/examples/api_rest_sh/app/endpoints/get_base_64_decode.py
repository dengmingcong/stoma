"""Base64-url decode a value。

Generated from OpenAPI: get-base64-decode
"""

from __future__ import annotations

from stoma import APIRoute, ResponseSpec

from ..models import ErrorModel, GetBase64DecodeResponse
from ..router import router


@router.get("/base64/decode/{value}")
class GetBase64Decode(APIRoute):
    """Base64-url decode a value。"""

    value: str

    @property
    def on_200(self) -> ResponseSpec[GetBase64DecodeResponse]:
        return ResponseSpec(
            status_code=200,
            media_type="application/json",
            expected_type=GetBase64DecodeResponse,
        )

    @property
    def on_default(self) -> ResponseSpec[ErrorModel]:
        return ResponseSpec(
            status_code=lambda c: c not in [200],
            media_type="application/problem+json",
            expected_type=ErrorModel,
        )
