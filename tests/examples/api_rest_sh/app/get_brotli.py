"""Return an explicitly compressed response。

Generated from OpenAPI: get-brotli
"""

from __future__ import annotations

from .models import ErrorModel
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/brotli")
class GetBrotli(APIRoute[ErrorModel]):
    """Return an explicitly compressed response。"""
