"""Stream newline-delimited JSON logs。

Generated from OpenAPI: get-logs
"""

from __future__ import annotations

from .models import ErrorModel
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/logs")
class GetLogs(APIRoute[ErrorModel]):
    """Stream newline-delimited JSON logs。
    """
    count: int | None = None
