"""get-image。

Generated from OpenAPI: get-image
Get an image
"""

from __future__ import annotations

from .models import ErrorModel
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/images/{type}")
class GetImage(APIRoute[ErrorModel]):
    """get-image。
    Get an image
    """

    type: str
    """Image format to return"""
