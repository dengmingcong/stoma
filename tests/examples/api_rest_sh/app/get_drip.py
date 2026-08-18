"""Slowly stream bytes。

Generated from OpenAPI: get-drip
"""

from __future__ import annotations

from stoma import APIRoute, APIRouter

from .models import ErrorModel

router = APIRouter()


@router.get("/drip")
class GetDrip(APIRoute[ErrorModel]):
    """Slowly stream bytes。"""

    numbytes: int | None = None
    """Number of bytes to stream"""
    duration: str | None = None
    """Total duration over which bytes are emitted"""
    delay: str | None = None
    """Delay before streaming begins"""
    code: int | None = None
    """HTTP status code to return"""
