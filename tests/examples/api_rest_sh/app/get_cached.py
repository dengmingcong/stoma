"""None。

Generated from OpenAPI: get-cached
Cached response example
"""

from __future__ import annotations

from stoma import APIRoute, APIRouter

from .models import CachedModel, ErrorModel

router = APIRouter()


@router.get("/cached/{seconds}")
class GetCached(APIRoute[CachedModel | ErrorModel]):
    """None。
    Cached response example
    """

    seconds: int
    private: bool | None = None
