"""Return data using a specific media type。

Generated from OpenAPI: get-format
"""

from __future__ import annotations

from .models import GetFormatResponse
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/formats/{format}")
class GetFormat(APIRoute[GetFormatResponse]):
    """Return data using a specific media type。
    """
    format: str
