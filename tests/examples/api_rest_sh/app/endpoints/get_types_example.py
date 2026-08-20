"""
Generated from OpenAPI: get-types-example
Example structured data types
"""

from __future__ import annotations

from stoma import APIRoute

from ..models import ErrorModel, TypesModel
from ..router import router


@router.get("/types")
class GetTypesExample(APIRoute[TypesModel | ErrorModel]):
    """
    Example structured data types
    """
