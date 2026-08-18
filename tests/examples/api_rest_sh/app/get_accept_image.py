"""Return an image based on the Accept header。

Generated from OpenAPI: get-accept-image
"""

from __future__ import annotations

from stoma import APIRouter, APIRoute
from .models import ErrorModel

router = APIRouter()


@router.get("/image")
class GetAcceptImage(APIRoute[ErrorModel]):
    """Return an image based on the Accept header。"""
