"""Delay before responding。

Generated from OpenAPI: get-slow
"""

from __future__ import annotations

from stoma import APIRouter, APIRoute
from .models import GetSlowResponse, ErrorModel

router = APIRouter()


@router.get("/slow")
class GetSlow(APIRoute[GetSlowResponse | ErrorModel]):
    """Delay before responding。"""

    delay: str | None = None
    """Delay duration, for example 500ms or 2s"""
