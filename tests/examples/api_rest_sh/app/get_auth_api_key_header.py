"""Require an API key header。

Generated from OpenAPI: get-auth-api-key-header
"""

from __future__ import annotations

from .models import AuthResponseBody
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/auth/api-key-header")
class GetAuthApiKeyHeader(APIRoute[AuthResponseBody]):
    """Require an API key header。
    """
