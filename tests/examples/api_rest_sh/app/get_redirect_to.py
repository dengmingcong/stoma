"""Redirect to a supplied URL。

Generated from OpenAPI: get-redirect-to
"""

from __future__ import annotations

from .models import ErrorModel
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/redirect-to")
class GetRedirectTo(APIRoute[ErrorModel]):
    """Redirect to a supplied URL。
    """
    url: str
    status_code: int | None = None
