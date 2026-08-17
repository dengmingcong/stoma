"""Delay before responding。

Generated from OpenAPI: get-slow
"""

from __future__ import annotations

from stoma import APIRoute, APIRouter

from .models import ErrorModel, GetSlowResponse

router = APIRouter()


@router.get("/slow")
class GetSlow(APIRoute[GetSlowResponse | ErrorModel]):
    """Delay before responding。"""

    delay: str | None = None
