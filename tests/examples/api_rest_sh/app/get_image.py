"""None。

Generated from OpenAPI: get-image
Get an image
"""

from __future__ import annotations

from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/images/{type}")
class GetImage(APIRoute):
    """None。
    Get an image
    """
    type: str
