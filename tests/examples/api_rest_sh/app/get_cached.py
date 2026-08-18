"""get-cached。

Generated from OpenAPI: get-cached
Cached response example
"""

from __future__ import annotations

from .models import CachedModel, ErrorModel
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/cached/{seconds}")
class GetCached(APIRoute[CachedModel | ErrorModel]):
    """get-cached。
    Cached response example
    """

    seconds: int
    """Number of seconds to cache"""
    private: bool | None = None
    """Disable shared caches like CDNs"""
