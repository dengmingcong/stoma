"""Return request cookies。

Generated from OpenAPI: get-cookies
"""

from __future__ import annotations

from stoma import APIRouter, APIRoute
from .models import GetCookiesResponse, ErrorModel

router = APIRouter()


@router.get("/cookies")
class GetCookies(APIRoute[GetCookiesResponse | ErrorModel]):
    """Return request cookies。"""
