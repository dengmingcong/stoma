"""Exercise ETag conditional headers。

Generated from OpenAPI: get-etag
"""

from __future__ import annotations

from stoma import APIRoute, ResponseSpec

from ..models import ErrorModel
from ..router import router


@router.get("/etag/{etag}")
class GetEtag(APIRoute):
    """Exercise ETag conditional headers。"""

    etag: str
    """Opaque ETag value to return"""

    @property
    def on_default(self) -> ResponseSpec[ErrorModel]:
        return ResponseSpec(
            status_code=lambda c: c not in [204], media_type="application/problem+json", expected_type=ErrorModel
        )
