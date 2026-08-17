"""Return XML。

Generated from OpenAPI: get-xml
"""

from __future__ import annotations

from stoma import APIRoute, APIRouter

from .models import ErrorModel

router = APIRouter()


@router.get("/xml")
class GetXml(APIRoute[ErrorModel]):
    """Return XML。"""
