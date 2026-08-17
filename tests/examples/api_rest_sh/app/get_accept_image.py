"""Return an image based on the Accept header。

Generated from OpenAPI: get-accept-image
"""

from __future__ import annotations

from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/image")
class GetAcceptImage(APIRoute):
    """Return an image based on the Accept header。
    """
