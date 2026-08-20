"""Stream newline-delimited JSON logs。

Generated from OpenAPI: get-logs
"""

from __future__ import annotations

from stoma import APIRoute

from ..models import ErrorModel
from ..router import router


@router.get("/logs")
class GetLogs(APIRoute[ErrorModel]):
    """Stream newline-delimited JSON logs。"""

    count: int | None = None
    """Number of log lines to emit"""
