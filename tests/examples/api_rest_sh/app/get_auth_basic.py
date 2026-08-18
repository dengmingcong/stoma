"""Require HTTP Basic auth。

Generated from OpenAPI: get-auth-basic
"""

from __future__ import annotations

from stoma import APIRoute, APIRouter

from .models import AuthResponseBody, ErrorModel

router = APIRouter()


@router.get("/auth/basic")
class GetAuthBasic(APIRoute[AuthResponseBody | ErrorModel]):
    """Require HTTP Basic auth。"""
