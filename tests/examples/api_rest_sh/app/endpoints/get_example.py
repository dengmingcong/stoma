"""
Generated from OpenAPI: get-example
Example large structured data response
"""

from __future__ import annotations

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel, Resume
from ..router import router


@router.get("/example")
class GetExample(APIRoute):
    """
    Example large structured data response
    """

    @property
    def on_200(self) -> JSONResponseSpec[Resume]:
        return JSONResponseSpec(status_code=200, media_type="application/json", model=Resume)

    @property
    def on_default(self) -> JSONResponseSpec[ErrorModel]:
        return JSONResponseSpec(
            status_code=lambda c: c not in [200], media_type="application/problem+json", model=ErrorModel
        )
