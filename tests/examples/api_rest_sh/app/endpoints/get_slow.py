"""Delay before responding。

Generated from OpenAPI: get-slow
"""

from __future__ import annotations

from typing import ClassVar

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel, GetSlowResponse
from ..router import router


@router.get("/slow")
class GetSlow(APIRoute):
    """Delay before responding。"""

    on_200: ClassVar[JSONResponseSpec] = JSONResponseSpec(
        status_code=200, media_type="application/json", model=GetSlowResponse
    )
    on_default: ClassVar[JSONResponseSpec] = JSONResponseSpec(
        callable=lambda s: True, media_type="application/problem+json", model=ErrorModel
    )
    delay: str | None = None
    """Delay duration, for example 500ms or 2s"""
