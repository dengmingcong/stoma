"""Require bearer token auth。

Generated from OpenAPI: get-auth-bearer
"""

from __future__ import annotations

from .models import AuthResponseBody, ErrorModel
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/auth/bearer")
class GetAuthBearer(APIRoute[AuthResponseBody | ErrorModel]):
    """Require bearer token auth。
    """
