"""Set cookies from query parameters。

Generated from OpenAPI: get-cookies-set
"""

from __future__ import annotations

from stoma import APIRoute

from ..models import ErrorModel, GetCookiesSetResponse
from ..router import router


@router.get("/cookies/set")
class GetCookiesSet(APIRoute[GetCookiesSetResponse | ErrorModel]):
    """Set cookies from query parameters。"""
