"""Return XML。

Generated from OpenAPI: get-xml
"""

from __future__ import annotations

from .models import GetXmlResponse
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/xml")
class GetXml(APIRoute[GetXmlResponse]):
    """Return XML。
    """
