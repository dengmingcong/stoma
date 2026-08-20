"""Require an API key header。

Generated from OpenAPI: get-auth-api-key-header
"""

from __future__ import annotations

from stoma import APIRoute

from ..models import AuthResponseBody, ErrorModel
from ..router import router


@router.get("/auth/api-key-header")
class GetAuthApiKeyHeader(APIRoute[AuthResponseBody | ErrorModel]):
    """Require an API key header。"""
