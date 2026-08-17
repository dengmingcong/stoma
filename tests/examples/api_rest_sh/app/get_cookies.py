"""Return request cookies。

Generated from OpenAPI: get-cookies
"""

from __future__ import annotations

from stoma import APIRoute, APIRouter

from .models import ErrorModel, GetCookiesResponse

router = APIRouter()


@router.get("/cookies")
class GetCookies(APIRoute[GetCookiesResponse | ErrorModel]):
    """Return request cookies。"""
