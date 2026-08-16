"""Delay before responding。

Generated from OpenAPI: get-slow
"""

from __future__ import annotations

from .models import GetSlowResponse
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/slow")
class GetSlow(APIRoute[GetSlowResponse]):
    """Delay before responding。
    """
    delay: str | None = None
