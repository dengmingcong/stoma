"""Fail a configurable number of times, then succeed。

Generated from OpenAPI: get-flaky
"""

from __future__ import annotations

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel, GetFlakyResponse
from ..router import router


@router.get("/flaky")
class GetFlaky(APIRoute):
    """Fail a configurable number of times, then succeed。"""

    failures: int | None = None
    """Number of failed attempts before returning success"""
    key: str | None = None
    """Counter key used to isolate retry sequences"""

    @property
    def on_200(self) -> JSONResponseSpec[GetFlakyResponse]:
        return JSONResponseSpec(status_code=200, media_type="application/json", model=GetFlakyResponse)

    @property
    def on_default(self) -> JSONResponseSpec[ErrorModel]:
        return JSONResponseSpec(
            status_code=lambda c: c not in [200], media_type="application/problem+json", model=ErrorModel
        )
