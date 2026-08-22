"""
Generated from OpenAPI: get-image
Get an image
"""

from __future__ import annotations

from typing import ClassVar

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel
from ..router import router


@router.get("/images/{type}")
class GetImage(APIRoute):
    """
    Get an image
    """

    on_default: ClassVar[JSONResponseSpec] = JSONResponseSpec(
        callable=lambda s: True, media_type="application/problem+json", model=ErrorModel
    )
    type: str
    """Image format to return"""
