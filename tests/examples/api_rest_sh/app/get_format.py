"""Return data using a specific media type。

Generated from OpenAPI: get-format
"""

from __future__ import annotations

from .models import ErrorModel
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/formats/{format}")
class GetFormat(APIRoute[ErrorModel]):
    """Return data using a specific media type。"""

    format: str
    """Response format to encode"""
