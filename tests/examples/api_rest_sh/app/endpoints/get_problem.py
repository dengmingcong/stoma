"""Return an RFC 7807 problem document。

Generated from OpenAPI: get-problem
"""

from __future__ import annotations

from stoma import APIRoute, ResponseSpec

from ..models import ErrorModel, GetProblemResponse
from ..router import router


@router.get("/problem")
class GetProblem(APIRoute):
    """Return an RFC 7807 problem document。"""

    @property
    def on_200(self) -> ResponseSpec[GetProblemResponse]:
        return ResponseSpec(
            status_code=200,
            media_type="application/json",
            expected_type=GetProblemResponse,
        )

    @property
    def on_default(self) -> ResponseSpec[ErrorModel]:
        return ResponseSpec(
            status_code=lambda c: c not in [200],
            media_type="application/problem+json",
            expected_type=ErrorModel,
        )
