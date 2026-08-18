"""Fail a configurable number of times, then succeed。

Generated from OpenAPI: get-flaky
"""

from __future__ import annotations

from stoma import APIRouter, APIRoute
from .models import GetFlakyResponse, ErrorModel

router = APIRouter()


@router.get("/flaky")
class GetFlaky(APIRoute[GetFlakyResponse | ErrorModel]):
    """Fail a configurable number of times, then succeed。"""

    failures: int | None = None
    """Number of failed attempts before returning success"""
    key: str | None = None
    """Counter key used to isolate retry sequences"""
