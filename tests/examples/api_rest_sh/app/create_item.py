"""Create a sample item。

Generated from OpenAPI: create-item
"""

from __future__ import annotations

from stoma import APIRoute, APIRouter

from .models import ErrorModel, Item

router = APIRouter()


@router.post("/items")
class CreateItem(APIRoute[Item | ErrorModel]):
    """Create a sample item。"""

    body: Item
