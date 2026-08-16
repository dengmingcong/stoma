"""None。

Generated from OpenAPI: get-types-example
Example structured data types
"""

from __future__ import annotations

from .models import TypesModel
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/types")
class GetTypesExample(APIRoute[TypesModel]):
    """None。
    Example structured data types
    """
