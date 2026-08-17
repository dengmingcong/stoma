"""Stream newline-delimited JSON logs。

Generated from OpenAPI: get-logs
"""

from __future__ import annotations

from stoma import APIRoute, APIRouter

from .models import ErrorModel

router = APIRouter()


@router.get("/logs")
class GetLogs(APIRoute[ErrorModel]):
    """Stream newline-delimited JSON logs。"""

    count: int | None = None
