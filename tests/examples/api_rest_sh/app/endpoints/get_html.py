"""Return HTML。

Generated from OpenAPI: get-html
"""

from __future__ import annotations

from stoma import APIRoute

from ..models import ErrorModel
from ..router import router


@router.get("/html")
class GetHtml(APIRoute[ErrorModel]):
    """Return HTML。"""
