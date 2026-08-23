"""
Generated from OpenAPI: get-cached
Cached response example
"""

from __future__ import annotations

from stoma import APIRoute, ResponseSpec

from ..models import CachedModel, ErrorModel
from ..router import router


@router.get("/cached/{seconds}")
class GetCached(APIRoute):
    """
    Cached response example
    """

    seconds: int
    """Number of seconds to cache"""
    private: bool | None = None
    """Disable shared caches like CDNs"""

    @property
    def on_200(self) -> ResponseSpec[CachedModel]:
        return ResponseSpec(status_code=200, media_type="application/json", expected_type=CachedModel)

    @property
    def on_default(self) -> ResponseSpec[ErrorModel]:
        return ResponseSpec(
            status_code=lambda c: c not in [200], media_type="application/problem+json", expected_type=ErrorModel
        )
