"""Require an API key header。

Generated from OpenAPI: get-auth-api-key-header
"""

from __future__ import annotations

from stoma import APIRouter, APIRoute
from .models import AuthResponseBody, ErrorModel

router = APIRouter()


@router.get("/auth/api-key-header")
class GetAuthApiKeyHeader(APIRoute[AuthResponseBody | ErrorModel]):
    """Require an API key header。"""
