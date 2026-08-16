"""None。

Generated from OpenAPI: get-example
Example large structured data response
"""

from __future__ import annotations

from .models import Resume
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/example")
class GetExample(APIRoute[Resume]):
    """None。
    Example large structured data response
    """
