"""Return the User-Agent header。

Generated from OpenAPI: get-user-agent
"""

from __future__ import annotations

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel, GetUserAgentResponse
from ..router import router


@router.get("/user-agent")
class GetUserAgent(APIRoute):
    """Return the User-Agent header。"""

    @property
    def on_200(self) -> JSONResponseSpec[GetUserAgentResponse]:
        return JSONResponseSpec(status_code=200, media_type="application/json", model=GetUserAgentResponse)

    @property
    def on_default(self) -> JSONResponseSpec[ErrorModel]:
        return JSONResponseSpec(
            status_code=lambda c: c not in [200], media_type="application/problem+json", model=ErrorModel
        )
