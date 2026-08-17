"""None。

Generated from OpenAPI: get-image
Get an image
"""

from __future__ import annotations

from stoma import APIRoute, APIRouter

from .models import ErrorModel

router = APIRouter()


@router.get("/images/{type}")
class GetImage(APIRoute[ErrorModel]):
    """None。
    Get an image
    """

    type: str
