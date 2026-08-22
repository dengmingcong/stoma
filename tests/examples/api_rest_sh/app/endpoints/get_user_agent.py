"""Return the User-Agent header。

Generated from OpenAPI: get-user-agent
"""

from __future__ import annotations

from typing import ClassVar

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel, GetUserAgentResponse
from ..router import router


@router.get("/user-agent")
class GetUserAgent(APIRoute):
    """Return the User-Agent header。"""

    on_200: ClassVar[JSONResponseSpec] = JSONResponseSpec(
        status_code=200, media_type="application/json", model=GetUserAgentResponse
    )
    on_default: ClassVar[JSONResponseSpec] = JSONResponseSpec(
        callable=lambda s: True, media_type="application/problem+json", model=ErrorModel
    )
