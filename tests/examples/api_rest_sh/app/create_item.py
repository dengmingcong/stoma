"""Create a sample item。

Generated from OpenAPI: create-item
"""

from __future__ import annotations

from typing import Annotated

from stoma import APIRoute, APIRouter, Body

from .models import ErrorModel, Item

router = APIRouter()


@router.post("/items")
class CreateItem(APIRoute[Item | ErrorModel]):
    """Create a sample item。"""

    body: Item
