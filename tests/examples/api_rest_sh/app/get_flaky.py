"""Fail a configurable number of times, then succeed。

Generated from OpenAPI: get-flaky
"""

from __future__ import annotations

from .models import GetFlakyResponse, ErrorModel
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/flaky")
class GetFlaky(APIRoute[GetFlakyResponse | ErrorModel]):
    """Fail a configurable number of times, then succeed。
    """
    failures: int | None = None
    key: str | None = None
