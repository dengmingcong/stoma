"""None。

Generated from OpenAPI: get-example
Example large structured data response
"""

from __future__ import annotations

from stoma import APIRoute, APIRouter

from .models import ErrorModel, Resume

router = APIRouter()


@router.get("/example")
class GetExample(APIRoute[Resume | ErrorModel]):
    """None。
    Example large structured data response
    """
