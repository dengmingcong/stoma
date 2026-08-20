"""Delete cookies named by query parameters。

Generated from OpenAPI: get-cookies-delete
"""

from __future__ import annotations

from stoma import APIRoute

from ..models import ErrorModel, GetCookiesDeleteResponse
from ..router import router


@router.get("/cookies/delete")
class GetCookiesDelete(APIRoute[GetCookiesDeleteResponse | ErrorModel]):
    """Delete cookies named by query parameters。"""
