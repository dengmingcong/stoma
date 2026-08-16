"""Slowly stream bytes。

Generated from OpenAPI: get-drip
"""

from __future__ import annotations

from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/drip")
class GetDrip(APIRoute):
    """Slowly stream bytes。
    """
    numbytes: int | None = None
    duration: str | None = None
    delay: str | None = None
    code: int | None = None
