"""
Generated from OpenAPI: get-example
Example large structured data response
"""

from __future__ import annotations

from stoma import APIRoute, ResponseSpec

from ..models import ErrorModel, Resume
from ..router import router


@router.get("/example")
class GetExample(APIRoute):
    """
    Example large structured data response
    """

    @property
    def on_200(self) -> ResponseSpec[Resume]:
        return ResponseSpec(status_code=200, media_type="application/json", expected_type=Resume)

    @property
    def on_default(self) -> ResponseSpec[ErrorModel]:
        return ResponseSpec(
            status_code=lambda c: c not in [200], media_type="application/problem+json", expected_type=ErrorModel
        )
