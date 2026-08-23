"""Delay before responding。

Generated from OpenAPI: get-slow
"""

from __future__ import annotations

from stoma import APIRoute, ResponseSpec

from ..models import ErrorModel, GetSlowResponse
from ..router import router


@router.get("/slow")
class GetSlow(APIRoute):
    """Delay before responding。"""

    delay: str | None = None
    """Delay duration, for example 500ms or 2s"""

    @property
    def on_200(self) -> ResponseSpec[GetSlowResponse]:
        return ResponseSpec(status_code=200, media_type="application/json", expected_type=GetSlowResponse)

    @property
    def on_default(self) -> ResponseSpec[ErrorModel]:
        return ResponseSpec(
            status_code=lambda c: c not in [200], media_type="application/problem+json", expected_type=ErrorModel
        )
