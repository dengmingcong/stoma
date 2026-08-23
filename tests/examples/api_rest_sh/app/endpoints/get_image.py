"""
Generated from OpenAPI: get-image
Get an image
"""

from __future__ import annotations

from stoma import APIRoute, ResponseSpec

from ..models import ErrorModel
from ..router import router


@router.get("/images/{type}")
class GetImage(APIRoute):
    """
    Get an image
    """

    type: str
    """Image format to return"""

    @property
    def on_default(self) -> ResponseSpec[ErrorModel]:
        return ResponseSpec(
            status_code=lambda c: c not in [200], media_type="application/problem+json", expected_type=ErrorModel
        )
