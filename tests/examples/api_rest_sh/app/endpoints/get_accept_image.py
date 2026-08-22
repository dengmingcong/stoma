"""Return an image based on the Accept header。

Generated from OpenAPI: get-accept-image
"""

from __future__ import annotations

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel
from ..router import router


@router.get("/image")
class GetAcceptImage(APIRoute):
    """Return an image based on the Accept header。"""

    @property
    def on_default(self) -> JSONResponseSpec[ErrorModel]:
        return JSONResponseSpec(
            status_code=lambda c: c not in [200], media_type="application/problem+json", model=ErrorModel
        )
