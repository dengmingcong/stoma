"""
Generated from OpenAPI: get-example
Example large structured data response
"""

from __future__ import annotations

from stoma import APIRoute

from ..models import ErrorModel, Resume
from ..router import router


@router.get("/example")
class GetExample(APIRoute[Resume | ErrorModel]):
    """
    Example large structured data response
    """
