"""Return an RFC 7807 problem document。

Generated from OpenAPI: get-problem
"""

from __future__ import annotations

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel, GetProblemResponse
from ..router import router


@router.get("/problem")
class GetProblem(APIRoute):
    """Return an RFC 7807 problem document。"""

    @property
    def on_200(self) -> JSONResponseSpec[GetProblemResponse]:
        return JSONResponseSpec(status_code=200, media_type="application/json", model=GetProblemResponse)

    @property
    def on_default(self) -> JSONResponseSpec[ErrorModel]:
        return JSONResponseSpec(
            status_code=lambda c: c not in [200], media_type="application/problem+json", model=ErrorModel
        )
