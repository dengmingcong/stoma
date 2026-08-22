"""
Generated from OpenAPI: get-cached
Cached response example
"""

from __future__ import annotations

from typing import ClassVar

from stoma import APIRoute, JSONResponseSpec

from ..models import CachedModel, ErrorModel
from ..router import router


@router.get("/cached/{seconds}")
class GetCached(APIRoute):
    """
    Cached response example
    """

    on_200: ClassVar[JSONResponseSpec[CachedModel]] = JSONResponseSpec(
        status_code=200, media_type="application/json", model=CachedModel
    )
    on_default: ClassVar[JSONResponseSpec[ErrorModel]] = JSONResponseSpec(
        callable=lambda s: True, media_type="application/problem+json", model=ErrorModel
    )
    seconds: int
    """Number of seconds to cache"""
    private: bool | None = None
    """Disable shared caches like CDNs"""
