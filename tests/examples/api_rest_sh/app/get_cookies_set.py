"""Set cookies from query parameters。

Generated from OpenAPI: get-cookies-set
"""

from __future__ import annotations

from stoma import APIRouter, APIRoute
from .models import GetCookiesSetResponse, ErrorModel

router = APIRouter()


@router.get("/cookies/set")
class GetCookiesSet(APIRoute[GetCookiesSetResponse | ErrorModel]):
    """Set cookies from query parameters。"""
