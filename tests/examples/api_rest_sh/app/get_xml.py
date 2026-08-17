"""Return XML。

Generated from OpenAPI: get-xml
"""

from __future__ import annotations

from .models import ErrorModel
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/xml")
class GetXml(APIRoute[ErrorModel]):
    """Return XML。
    """
