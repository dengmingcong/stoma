"""
Generated from OpenAPI: get-example
Example large structured data response
"""

from __future__ import annotations

from typing import ClassVar

from stoma import APIRoute, JSONResponseSpec

from ..models import ErrorModel, Resume
from ..router import router


@router.get("/example")
class GetExample(APIRoute):
    """
    Example large structured data response
    """

    on_200: ClassVar[JSONResponseSpec] = JSONResponseSpec(status_code=200, media_type="application/json", model=Resume)
    on_default: ClassVar[JSONResponseSpec] = JSONResponseSpec(
        callable=lambda s: True, media_type="application/problem+json", model=ErrorModel
    )
