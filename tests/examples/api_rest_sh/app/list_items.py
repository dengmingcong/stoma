"""List sample items。

Generated from OpenAPI: list-items
"""

from __future__ import annotations

from .models import ListItemsResponse
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/items")
class ListItems(APIRoute[ListItemsResponse]):
    """List sample items。
    """
