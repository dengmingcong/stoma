"""Require an API key query parameter。

Generated from OpenAPI: get-auth-api-key-query
"""

from __future__ import annotations

from stoma import APIRoute, APIRouter

from .models import AuthResponseBody, ErrorModel

router = APIRouter()


@router.get("/auth/api-key-query")
class GetAuthApiKeyQuery(APIRoute[AuthResponseBody | ErrorModel]):
    """Require an API key query parameter。"""

    api_key: str | None = None
