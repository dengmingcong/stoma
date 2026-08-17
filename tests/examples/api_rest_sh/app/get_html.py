"""Return HTML。

Generated from OpenAPI: get-html
"""

from __future__ import annotations

from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/html")
class GetHtml(APIRoute):
    """Return HTML。
    """
