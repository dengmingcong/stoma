"""Return a UUID。

Generated from OpenAPI: get-uuid
"""

from __future__ import annotations

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel, GetUuidResponse
from ..router import router


@router.get("/uuid")
class GetUuid(APIRoute):
    """Return a UUID。"""

    @property
    def on_200(self) -> JSONResponseSpec[GetUuidResponse]:
        return JSONResponseSpec(status_code=200, media_type="application/json", model=GetUuidResponse)

    @property
    def on_default(self) -> JSONResponseSpec[ErrorModel]:
        return JSONResponseSpec(
            status_code=lambda c: c not in [200], media_type="application/problem+json", model=ErrorModel
        )
