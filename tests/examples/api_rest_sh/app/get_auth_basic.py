"""Require HTTP Basic auth。

Generated from OpenAPI: get-auth-basic
"""

from __future__ import annotations

from .models import AuthResponseBody
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/auth/basic")
class GetAuthBasic(APIRoute[AuthResponseBody]):
    """Require HTTP Basic auth。
    """
