"""List sample items。

Generated from OpenAPI: list-items
"""

from __future__ import annotations

from stoma import APIRoute, APIRouter

from .models import ErrorModel, ListItemsResponse

router = APIRouter()


@router.get("/items")
class ListItems(APIRoute[ListItemsResponse | ErrorModel]):
    """List sample items。"""
