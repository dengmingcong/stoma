"""List sample items。

Generated from OpenAPI: list-items
"""

from __future__ import annotations

from stoma import APIRouter, APIRoute
from .models import ListItemsResponse, ErrorModel

router = APIRouter()


@router.get("/items")
class ListItems(APIRoute[ListItemsResponse | ErrorModel]):
    """List sample items。"""
