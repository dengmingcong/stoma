"""
Generated from OpenAPI: get-example
Example large structured data response
"""

from __future__ import annotations

from stoma import APIRouter, APIRoute
from .models import Resume, ErrorModel

router = APIRouter()


@router.get("/example")
class GetExample(APIRoute[Resume | ErrorModel]):
    """
    Example large structured data response
    """
