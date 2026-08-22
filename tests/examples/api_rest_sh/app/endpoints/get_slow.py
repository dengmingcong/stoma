"""Delay before responding。

Generated from OpenAPI: get-slow
"""

from __future__ import annotations

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel, GetSlowResponse
from ..router import router


@router.get("/slow")
class GetSlow(APIRoute):
    """Delay before responding。"""

    delay: str | None = None
    """Delay duration, for example 500ms or 2s"""

    @property
    def on_200(self) -> JSONResponseSpec[GetSlowResponse]:
        return JSONResponseSpec(status_code=200, media_type="application/json", model=GetSlowResponse)

    @property
    def on_default(self) -> JSONResponseSpec[ErrorModel]:
        return JSONResponseSpec(
            status_code=lambda c: c not in [200], media_type="application/problem+json", model=ErrorModel
        )
