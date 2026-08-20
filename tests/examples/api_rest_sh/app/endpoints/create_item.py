"""Create a sample item。

Generated from OpenAPI: create-item
"""

from __future__ import annotations

from stoma import APIRoute

from ..models import ErrorModel, Item
from ..router import router


@router.post("/items")
class CreateItem(APIRoute[Item | ErrorModel]):
    """Create a sample item。"""

    body: Item
