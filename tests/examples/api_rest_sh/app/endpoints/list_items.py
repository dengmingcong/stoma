"""List sample items。

Generated from OpenAPI: list-items
"""

from __future__ import annotations

from stoma import APIRoute

from ..models import ErrorModel, ListItemsResponse
from ..router import router


@router.get("/items")
class ListItems(APIRoute[ListItemsResponse | ErrorModel]):
    """List sample items。"""
