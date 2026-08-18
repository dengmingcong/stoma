"""Delay before responding。

Generated from OpenAPI: get-slow
"""

from __future__ import annotations

from .models import GetSlowResponse, ErrorModel
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/slow")
class GetSlow(APIRoute[GetSlowResponse | ErrorModel]):
    """Delay before responding。"""

    delay: str | None = None
    """Delay duration, for example 500ms or 2s"""
