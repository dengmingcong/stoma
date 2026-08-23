"""Stream newline-delimited JSON logs。

Generated from OpenAPI: get-logs
"""

from __future__ import annotations

from stoma import APIRoute, ResponseSpec

from ..models import ErrorModel
from ..router import router


@router.get("/logs")
class GetLogs(APIRoute):
    """Stream newline-delimited JSON logs。"""

    count: int | None = None
    """Number of log lines to emit"""

    @property
    def on_default(self) -> ResponseSpec[ErrorModel]:
        return ResponseSpec(
            status_code=lambda c: c not in [200], media_type="application/problem+json", expected_type=ErrorModel
        )
