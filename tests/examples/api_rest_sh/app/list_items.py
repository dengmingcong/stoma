"""List sample items。

Generated from OpenAPI: list-items
"""

from __future__ import annotations

from .models import ListItemsResponse, ErrorModel
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/items")
class ListItems(APIRoute[ListItemsResponse | ErrorModel]):
    """List sample items。"""
