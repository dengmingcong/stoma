"""Return a UUID。

Generated from OpenAPI: get-uuid
"""

from __future__ import annotations

from stoma import APIRoute, ResponseSpec

from ..models import ErrorModel, GetUuidResponse
from ..router import router


@router.get("/uuid")
class GetUuid(APIRoute):
    """Return a UUID。"""

    @property
    def on_200(self) -> ResponseSpec[GetUuidResponse]:
        return ResponseSpec(status_code=200, media_type="application/json", expected_type=GetUuidResponse)

    @property
    def on_default(self) -> ResponseSpec[ErrorModel]:
        return ResponseSpec(
            status_code=lambda c: c not in [200], media_type="application/problem+json", expected_type=ErrorModel
        )
