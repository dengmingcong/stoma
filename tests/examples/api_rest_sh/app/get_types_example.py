"""
Generated from OpenAPI: get-types-example
Example structured data types
"""

from __future__ import annotations

from stoma import APIRoute, APIRouter

from .models import ErrorModel, TypesModel

router = APIRouter()


@router.get("/types")
class GetTypesExample(APIRoute[TypesModel | ErrorModel]):
    """
    Example structured data types
    """
