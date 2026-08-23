"""Fail a configurable number of times, then succeed。

Generated from OpenAPI: get-flaky
"""

from __future__ import annotations

from stoma import APIRoute, ResponseSpec

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
    def on_200(self) -> ResponseSpec[GetFlakyResponse]:
        return ResponseSpec(
            status_code=200,
            media_type="application/json",
            expected_type=GetFlakyResponse,
        )

    @property
    def on_default(self) -> ResponseSpec[ErrorModel]:
        return ResponseSpec(
            status_code=lambda c: c not in [200],
            media_type="application/problem+json",
            expected_type=ErrorModel,
        )
