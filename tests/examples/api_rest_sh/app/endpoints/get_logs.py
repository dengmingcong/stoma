"""Stream newline-delimited JSON logs。

Generated from OpenAPI: get-logs
"""

from __future__ import annotations

from typing import ClassVar

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel
from ..router import router


@router.get("/logs")
class GetLogs(APIRoute):
    """Stream newline-delimited JSON logs。"""

    on_default: ClassVar[JSONResponseSpec[ErrorModel]] = JSONResponseSpec(
        callable=lambda s: True, media_type="application/problem+json", model=ErrorModel
    )
    count: int | None = None
    """Number of log lines to emit"""
