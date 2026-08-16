"""Delete cookies named by query parameters。

Generated from OpenAPI: get-cookies-delete
"""

from __future__ import annotations

from .models import GetCookiesDeleteResponse
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/cookies/delete")
class GetCookiesDelete(APIRoute[GetCookiesDeleteResponse]):
    """Delete cookies named by query parameters。
    """
