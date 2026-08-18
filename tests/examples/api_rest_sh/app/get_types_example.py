"""
Generated from OpenAPI: get-types-example
Example structured data types
"""

from __future__ import annotations

from stoma import APIRouter, APIRoute
from .models import TypesModel, ErrorModel

router = APIRouter()


@router.get("/types")
class GetTypesExample(APIRoute[TypesModel | ErrorModel]):
    """
    Example structured data types
    """
