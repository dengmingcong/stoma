"""Get a sample item。

Generated from OpenAPI: get-item
"""

from __future__ import annotations

from .models import Item
from typing import Annotated
from pydantic import Field
from stoma import APIRouter, APIRoute

router = APIRouter()


@router.get("/items/{item-id}")
class GetItem(APIRoute[Item]):
    """Get a sample item。
    """
    item_id: Annotated[str, Field(serialization_alias='item-id')]
