"""Return data using a specific media type。

Generated from OpenAPI: get-format
"""

from __future__ import annotations

from stoma import APIRoute

from ..models import ErrorModel
from ..router import router


@router.get("/formats/{format}")
class GetFormat(APIRoute[ErrorModel]):
    """Return data using a specific media type。"""

    format: str
    """Response format to encode"""
