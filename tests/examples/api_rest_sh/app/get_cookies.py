"""Return request cookies。

Generated from OpenAPI: get-cookies
"""

from __future__ import annotations

from .models import GetCookiesResponse
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/cookies")
class GetCookies(APIRoute[GetCookiesResponse]):
    """Return request cookies。
    """
