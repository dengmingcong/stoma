"""Exercise ETag conditional headers。

Generated from OpenAPI: get-etag
"""

from __future__ import annotations

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel
from ..router import router


@router.get("/etag/{etag}")
class GetEtag(APIRoute):
    """Exercise ETag conditional headers。"""

    etag: str
    """Opaque ETag value to return"""

    @property
    def on_default(self) -> JSONResponseSpec[ErrorModel]:
        return JSONResponseSpec(
            status_code=lambda c: c not in [204], media_type="application/problem+json", model=ErrorModel
        )
