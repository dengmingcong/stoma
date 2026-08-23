"""Return the requester IP。

Generated from OpenAPI: get-ip
"""

from __future__ import annotations

from stoma import APIRoute, ResponseSpec

from ..models import ErrorModel, GetIpResponse
from ..router import router


@router.get("/ip")
class GetIp(APIRoute):
    """Return the requester IP。"""

    @property
    def on_200(self) -> ResponseSpec[GetIpResponse]:
        return ResponseSpec(status_code=200, media_type="application/json", expected_type=GetIpResponse)

    @property
    def on_default(self) -> ResponseSpec[ErrorModel]:
        return ResponseSpec(
            status_code=lambda c: c not in [200], media_type="application/problem+json", expected_type=ErrorModel
        )
