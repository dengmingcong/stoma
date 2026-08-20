"""Return XML。

Generated from OpenAPI: get-xml
"""

from __future__ import annotations

from stoma import APIRoute

from ..models import ErrorModel
from ..router import router


@router.get("/xml")
class GetXml(APIRoute[ErrorModel]):
    """Return XML。"""
