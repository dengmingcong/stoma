"""Redirect to a supplied URL。

Generated from OpenAPI: get-redirect-to
"""

from __future__ import annotations

from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/redirect-to")
class GetRedirectTo(APIRoute):
    """Redirect to a supplied URL。
    """
    url: str
    status_code: int | None = None
