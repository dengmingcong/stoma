"""Return the requester IP。

Generated from OpenAPI: get-ip
"""

from __future__ import annotations

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel, GetIpResponse
from ..router import router


@router.get("/ip")
class GetIp(APIRoute):
    """Return the requester IP。"""

    @property
    def on_200(self) -> JSONResponseSpec[GetIpResponse]:
        return JSONResponseSpec(status_code=200, media_type="application/json", model=GetIpResponse)

    @property
    def on_default(self) -> JSONResponseSpec[ErrorModel]:
        return JSONResponseSpec(
            status_code=lambda c: c not in [200], media_type="application/problem+json", model=ErrorModel
        )
