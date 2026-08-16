"""Return an explicitly compressed response。

Generated from OpenAPI: get-gzip
"""

from __future__ import annotations

from .models import GetGzipResponse
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/gzip")
class GetGzip(APIRoute[GetGzipResponse]):
    """Return an explicitly compressed response。
    """
