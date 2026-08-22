"""Return a UUID。

Generated from OpenAPI: get-uuid
"""

from __future__ import annotations

from typing import ClassVar

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel, GetUuidResponse
from ..router import router


@router.get("/uuid")
class GetUuid(APIRoute):
    """Return a UUID。"""

    on_200: ClassVar[JSONResponseSpec] = JSONResponseSpec(
        status_code=200, media_type="application/json", model=GetUuidResponse
    )
    on_default: ClassVar[JSONResponseSpec] = JSONResponseSpec(
        callable=lambda s: True, media_type="application/problem+json", model=ErrorModel
    )
