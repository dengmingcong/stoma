"""
Generated from OpenAPI: get-image
Get an image
"""

from __future__ import annotations

from stoma import APIRoute

from ..models import ErrorModel
from ..router import router


@router.get("/images/{type}")
class GetImage(APIRoute[ErrorModel]):
    """
    Get an image
    """

    type: str
    """Image format to return"""
