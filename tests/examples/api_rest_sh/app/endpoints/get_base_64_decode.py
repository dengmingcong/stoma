"""Base64-url decode a value。

Generated from OpenAPI: get-base64-decode
"""

from __future__ import annotations

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel, GetBase64DecodeResponse
from ..router import router


@router.get("/base64/decode/{value}")
class GetBase64Decode(APIRoute):
    """Base64-url decode a value。"""

    value: str

    @property
    def on_200(self) -> JSONResponseSpec[GetBase64DecodeResponse]:
        return JSONResponseSpec(status_code=200, media_type="application/json", model=GetBase64DecodeResponse)

    @property
    def on_default(self) -> JSONResponseSpec[ErrorModel]:
        return JSONResponseSpec(
            status_code=lambda c: c not in [200], media_type="application/problem+json", model=ErrorModel
        )
