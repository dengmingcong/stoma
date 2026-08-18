"""Return HTML。

Generated from OpenAPI: get-html
"""

from __future__ import annotations

from stoma import APIRoute, APIRouter

from .models import ErrorModel

router = APIRouter()


@router.get("/html")
class GetHtml(APIRoute[ErrorModel]):
    """Return HTML。"""
