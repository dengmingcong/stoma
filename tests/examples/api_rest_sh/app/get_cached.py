"""None。

Generated from OpenAPI: get-cached
Cached response example
"""

from __future__ import annotations

from .models import CachedModel
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/cached/{seconds}")
class GetCached(APIRoute[CachedModel]):
    """None。
    Cached response example
    """
    seconds: int
    private: bool | None = None
