"""Delete cookies named by query parameters。

Generated from OpenAPI: get-cookies-delete
"""

from __future__ import annotations

from stoma import APIRouter, APIRoute
from .models import GetCookiesDeleteResponse, ErrorModel

router = APIRouter()


@router.get("/cookies/delete")
class GetCookiesDelete(APIRoute[GetCookiesDeleteResponse | ErrorModel]):
    """Delete cookies named by query parameters。"""
