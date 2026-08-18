"""Return an explicitly compressed response。

Generated from OpenAPI: get-brotli
"""

from __future__ import annotations

from stoma import APIRouter, APIRoute
from .models import ErrorModel

router = APIRouter()


@router.get("/brotli")
class GetBrotli(APIRoute[ErrorModel]):
    """Return an explicitly compressed response。"""
