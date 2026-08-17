"""Set cookies from query parameters。

Generated from OpenAPI: get-cookies-set
"""

from __future__ import annotations

from .models import GetCookiesSetResponse, ErrorModel
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/cookies/set")
class GetCookiesSet(APIRoute[GetCookiesSetResponse | ErrorModel]):
    """Set cookies from query parameters。
    """
