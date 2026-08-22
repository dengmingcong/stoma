"""Return request cookies。

Generated from OpenAPI: get-cookies
"""

from __future__ import annotations

from typing import ClassVar

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel, GetCookiesResponse
from ..router import router


@router.get("/cookies")
class GetCookies(APIRoute):
    """Return request cookies。"""

    on_200: ClassVar[JSONResponseSpec] = JSONResponseSpec(
        status_code=200, media_type="application/json", model=GetCookiesResponse
    )
    on_default: ClassVar[JSONResponseSpec] = JSONResponseSpec(
        callable=lambda s: True, media_type="application/problem+json", model=ErrorModel
    )
