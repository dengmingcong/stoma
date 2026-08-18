"""
Generated from OpenAPI: get-cached
Cached response example
"""

from __future__ import annotations

from stoma import APIRouter, APIRoute
from .models import CachedModel, ErrorModel

router = APIRouter()


@router.get("/cached/{seconds}")
class GetCached(APIRoute[CachedModel | ErrorModel]):
    """
    Cached response example
    """

    seconds: int
    """Number of seconds to cache"""
    private: bool | None = None
    """Disable shared caches like CDNs"""
