"""Create a sample item。

Generated from OpenAPI: create-item
"""

from __future__ import annotations

from .models import Item
from typing import Annotated
from stoma import APIRouter, APIRoute, Body

router = APIRouter()


@router.post("/items")
class CreateItem(APIRoute[Item]):
    """Create a sample item。
    """
    body: Item
