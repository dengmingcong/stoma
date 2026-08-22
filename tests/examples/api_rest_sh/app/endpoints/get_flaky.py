"""Fail a configurable number of times, then succeed。

Generated from OpenAPI: get-flaky
"""

from __future__ import annotations

from typing import ClassVar

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel, GetFlakyResponse
from ..router import router


@router.get("/flaky")
class GetFlaky(APIRoute):
    """Fail a configurable number of times, then succeed。"""

    on_200: ClassVar[JSONResponseSpec] = JSONResponseSpec(
        status_code=200, media_type="application/json", model=GetFlakyResponse
    )
    on_default: ClassVar[JSONResponseSpec] = JSONResponseSpec(
        callable=lambda s: True, media_type="application/problem+json", model=ErrorModel
    )
    failures: int | None = None
    """Number of failed attempts before returning success"""
    key: str | None = None
    """Counter key used to isolate retry sequences"""
