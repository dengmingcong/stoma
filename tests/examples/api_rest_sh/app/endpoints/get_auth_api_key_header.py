"""Require an API key header。

Generated from OpenAPI: get-auth-api-key-header
"""

from __future__ import annotations

from typing import ClassVar

from stoma import APIRoute, JSONResponseSpec

from ..models import AuthResponseBody, ErrorModel
from ..router import router


@router.get("/auth/api-key-header")
class GetAuthApiKeyHeader(APIRoute):
    """Require an API key header。"""

    on_200: ClassVar[JSONResponseSpec[AuthResponseBody]] = JSONResponseSpec(
        status_code=200, media_type="application/json", model=AuthResponseBody
    )
    on_default: ClassVar[JSONResponseSpec[ErrorModel]] = JSONResponseSpec(
        callable=lambda s: True, media_type="application/problem+json", model=ErrorModel
    )
