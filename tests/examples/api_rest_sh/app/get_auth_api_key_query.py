"""Require an API key query parameter。

Generated from OpenAPI: get-auth-api-key-query
"""

from __future__ import annotations

from .models import AuthResponseBody
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/auth/api-key-query")
class GetAuthApiKeyQuery(APIRoute[AuthResponseBody]):
    """Require an API key query parameter。
    """
    api_key: str | None = None
