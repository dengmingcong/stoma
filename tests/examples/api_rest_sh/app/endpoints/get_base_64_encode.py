"""Base64-url encode a value。

Generated from OpenAPI: get-base64-encode
"""

from __future__ import annotations

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel, GetBase64EncodeResponse
from ..router import router


@router.get("/base64/encode/{value}")
class GetBase64Encode(APIRoute):
    """Base64-url encode a value。"""

    value: str

    @property
    def on_200(self) -> JSONResponseSpec[GetBase64EncodeResponse]:
        return JSONResponseSpec(status_code=200, media_type="application/json", model=GetBase64EncodeResponse)

    @property
    def on_default(self) -> JSONResponseSpec[ErrorModel]:
        return JSONResponseSpec(
            status_code=lambda c: c not in [200], media_type="application/problem+json", model=ErrorModel
        )
