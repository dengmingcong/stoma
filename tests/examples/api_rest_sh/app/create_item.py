"""Create a sample item。

Generated from OpenAPI: create-item
"""

from __future__ import annotations

from stoma import APIRouter, APIRoute
from .models import Item, ErrorModel

router = APIRouter()


@router.post("/items")
class CreateItem(APIRoute[Item | ErrorModel]):
    """Create a sample item。"""

    body: Item
