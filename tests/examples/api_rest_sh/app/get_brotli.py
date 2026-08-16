"""Return an explicitly compressed response。

Generated from OpenAPI: get-brotli
"""

from __future__ import annotations

from .models import GetBrotliResponse
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/brotli")
class GetBrotli(APIRoute[GetBrotliResponse]):
    """Return an explicitly compressed response。
    """
