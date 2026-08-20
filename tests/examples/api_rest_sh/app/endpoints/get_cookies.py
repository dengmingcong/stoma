"""Return request cookies。

Generated from OpenAPI: get-cookies
"""

from __future__ import annotations

from stoma import APIRoute

from ..models import ErrorModel, GetCookiesResponse
from ..router import router


@router.get("/cookies")
class GetCookies(APIRoute[GetCookiesResponse | ErrorModel]):
    """Return request cookies。"""
