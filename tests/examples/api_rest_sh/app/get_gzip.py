"""Return an explicitly compressed response。

Generated from OpenAPI: get-gzip
"""

from __future__ import annotations

from stoma import APIRouter, APIRoute
from .models import ErrorModel

router = APIRouter()


@router.get("/gzip")
class GetGzip(APIRoute[ErrorModel]):
    """Return an explicitly compressed response。"""
