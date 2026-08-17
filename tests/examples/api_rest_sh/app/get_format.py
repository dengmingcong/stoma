"""Return data using a specific media type。

Generated from OpenAPI: get-format
"""

from __future__ import annotations

from stoma import APIRoute, APIRouter

from .models import ErrorModel

router = APIRouter()


@router.get("/formats/{format}")
class GetFormat(APIRoute[ErrorModel]):
    """Return data using a specific media type。"""

    format: str
